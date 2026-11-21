"""SQLite tabanlı işlem geçmişi ve denetim izi deposu."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from faturaguard.domain.chat import ChatTurn
from faturaguard.domain.correction import CorrectionJob


class SqliteCorrectionJobStore:
    """İş özetlerini SQLite'ta, tam XML diff'ini dosya sisteminde saklar."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._database = root / "faturaguard.sqlite3"
        self._diff_root = root / "diffs"
        self._initialize()

    def save(self, job: CorrectionJob) -> None:
        now = self._timestamp()
        payload = job.model_dump(mode="json", exclude={"diff"})
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (job_id, original_filename, original_sha256, created_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    original_filename = excluded.original_filename,
                    original_sha256 = excluded.original_sha256,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    job.job_id,
                    job.original_filename,
                    job.original_sha256,
                    now,
                    now,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def load(self, job_id: str) -> CorrectionJob:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"İşlem kaydı bulunamadı: {job_id}")
        job = CorrectionJob.model_validate_json(row["payload_json"])
        if job.diff_path:
            diff_file = Path(job.diff_path)
            if diff_file.is_file():
                job.diff = diff_file.read_text(encoding="utf-8")
        return job

    def append_chat_turn(self, job_id: str, turn: ChatTurn) -> CorrectionJob:
        """Uzun model çağrısında değişen kararları eski job kopyasıyla ezmez."""
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT payload_json FROM jobs WHERE job_id=?', (job_id,)).fetchone()
            if row is None:
                raise FileNotFoundError('İşlem kaydı bulunamadı.')
            payload = json.loads(row['payload_json'])
            payload['chat_history'] = [*payload.get('chat_history', []), turn.model_dump(mode='json')][-20:]
            connection.execute('UPDATE jobs SET payload_json=?, updated_at=? WHERE job_id=?',
                               (json.dumps(payload, ensure_ascii=False), self._timestamp(), job_id))
            connection.execute(
                'INSERT INTO audit_events(job_id, occurred_at, event_type, detail_json) VALUES(?,?,?,?)',
                (job_id, self._timestamp(), 'document_chat_answered', json.dumps({
                    'mode': turn.mode, 'finding_code': turn.finding_code,
                    'citation_count': len(turn.citations), 'raw_question_sent_to_provider': False,
                    'masked_conversation_sent': turn.masked_conversation_sent,
                    'providers': turn.providers, 'tools_used': turn.tools_used,
                    'failure_code': turn.failure_code, 'validation_issues': turn.validation_issues,
                    'repair_attempted': turn.repair_attempted,
                })),
            )
        return self.load(job_id)

    def store_diff(self, job_id: str, diff: str) -> Path:
        self._diff_root.mkdir(parents=True, exist_ok=True)
        target = self._diff_root / f"{job_id}.diff"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(diff, encoding="utf-8")
        temporary.replace(target)
        return target

    def append_event(
        self, job_id: str, event_type: str, detail: dict[str, Any] | None = None
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events (job_id, occurred_at, event_type, detail_json) VALUES (?, ?, ?, ?)",
                (
                    job_id,
                    self._timestamp(),
                    event_type,
                    json.dumps(detail or {}, ensure_ascii=False),
                ),
            )

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT occurred_at, event_type, detail_json
                FROM audit_events WHERE job_id = ? ORDER BY event_id
                """,
                (job_id,),
            ).fetchall()
        return [
            {
                "occurred_at": row["occurred_at"],
                "event_type": row["event_type"],
                "detail": json.loads(row["detail_json"]),
            }
            for row in rows
        ]

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT job_id, original_filename, original_sha256, created_at, updated_at, payload_json
                FROM jobs ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row['payload_json'])
            result.append({
                "job_id": row["job_id"],
                "original_filename": row["original_filename"],
                "original_sha256": row["original_sha256"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "report": payload['report'],
                "current_report": payload.get('corrected_report') or payload['report'],
                "has_correction": payload.get('corrected_report') is not None,
            })
        return result

    def _initialize(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    original_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                );
                CREATE INDEX IF NOT EXISTS idx_audit_events_job_id ON audit_events(job_id, event_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()
