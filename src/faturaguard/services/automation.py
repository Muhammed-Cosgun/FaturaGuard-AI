"""Kalıcı teslim kuyruğu ve n8n'in kullandığı tekil inceleme kayıtları."""

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import httpx


def correction_event(job):
    if not job.corrected_report or not job.corrected_sha256:
        return None
    applied = sorted(p.proposal_id for p in job.proposals if p.status == "applied")
    if not applied:
        return None
    identity = json.dumps([job.job_id, job.corrected_sha256, applied])
    return {
        "event_id": hashlib.sha256(identity.encode()).hexdigest(),
        "event": "faturaguard.correction_revalidated.v1",
        "job_id": job.job_id,
        "corrected_sha256": job.corrected_sha256,
        "applied_proposal_ids": applied,
        "validation_after": {
            "errors": job.corrected_report.summary.error_count,
            "warnings": job.corrected_report.summary.warning_count,
            "information": job.corrected_report.summary.info_count,
        },
    }


SCHEMA = """
CREATE TABLE IF NOT EXISTS automation_outbox (
 event_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt REAL NOT NULL DEFAULT 0, lease TEXT, last_error TEXT,
 created_at REAL NOT NULL, delivered_at REAL
);
CREATE TABLE IF NOT EXISTS automation_reviews (
 event_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL, lease TEXT, lease_until REAL NOT NULL,
 created_at REAL NOT NULL, notified_at REAL
);
"""


def enqueue(connection, event):
    if event:
        connection.execute(
            "INSERT OR IGNORE INTO automation_outbox(event_id,job_id,payload,created_at) VALUES(?,?,?,?)",
            (event["event_id"], event["job_id"], json.dumps(event), time.time()),
        )


class AutomationStore:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.database = root / "faturaguard.sqlite3"
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def claim_delivery(self, now=None):
        now = time.time() if now is None else now
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE automation_outbox SET status='failed',last_error='attempts_exhausted' "
                "WHERE status='sending' AND attempts>=6 AND next_attempt<=?", (now,),
            )
            row = connection.execute(
                "SELECT * FROM automation_outbox WHERE status IN ('pending','retry','sending') "
                "AND next_attempt<=? AND attempts<6 ORDER BY created_at LIMIT 1", (now,),
            ).fetchone()
            if not row:
                return None
            lease = secrets.token_hex(16)
            connection.execute(
                "UPDATE automation_outbox SET status='sending',attempts=attempts+1,lease=?,"
                "next_attempt=? WHERE event_id=?", (lease, now + 180, row["event_id"]),
            )
            return {**dict(row), "lease": lease, "attempts": row["attempts"] + 1}

    def finish_delivery(self, row, error=None, permanent=False, now=None):
        now = time.time() if now is None else now
        status = "delivered" if error is None else (
            "failed" if permanent or row["attempts"] >= 6 else "retry")
        with self.connect() as connection:
            connection.execute(
                "UPDATE automation_outbox SET status=?,last_error=?,next_attempt=?,delivered_at=? "
                "WHERE event_id=? AND lease=?",
                (status, error, now + min(30 * 2 ** (row["attempts"] - 1), 900),
                 now if error is None else None, row["event_id"], row["lease"]),
            )

    def claim_review(self, event_id, now=None):
        """Sadece yerel kuyrukta bulunan gerçek olay; gelen içerik doğru kabul edilmez."""
        now = time.time() if now is None else now
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute(
                "SELECT payload,job_id FROM automation_outbox WHERE event_id=?", (event_id,),
            ).fetchone()
            if not event:
                raise ValueError("Bilinmeyen olay.")
            old = connection.execute(
                "SELECT * FROM automation_reviews WHERE event_id=?", (event_id,),
            ).fetchone()
            if old and old["status"] == "notified":
                return {"event_id": event_id, "status": "duplicate", "should_notify": False}
            if old and old["lease_until"] > now:
                return {"event_id": event_id, "status": "busy", "should_notify": False}
            lease = secrets.token_hex(16)
            connection.execute(
                "INSERT INTO automation_reviews VALUES(?,?,?,'processing',?,?,?,NULL) "
                "ON CONFLICT(event_id) DO UPDATE SET status='processing',lease=excluded.lease,"
                "lease_until=excluded.lease_until",
                (event_id, event["job_id"], event["payload"], lease, now + 120, now),
            )
            payload = json.loads(event["payload"])
            counts = payload["validation_after"]
            return {"event_id": event_id, "status": "processing", "should_notify": True,
                    "lease": lease, "review": payload,
                    "subject": "FaturaGuard: yeniden doğrulama tamamlandı",
                    "message": f"Olay: {event_id}\nİşlem: {event['job_id']}\n"
                    f"{counts['errors']} hata, {counts['warnings']} uyarı, "
                    f"{counts['information']} bilgi.\n"
                    "Sonuç inceleme kaydıdır; imza veya GİB gönderim onayı değildir."}

    def complete_review(self, event_id, lease):
        with self.connect() as connection:
            updated = connection.execute(
                "UPDATE automation_reviews SET status='notified',notified_at=?,lease_until=0 "
                "WHERE event_id=? AND lease=? AND status IN ('processing','notified')",
                (time.time(), event_id, lease),
            ).rowcount
            if not updated:
                raise ValueError("İnceleme sahipliği eşleşmedi.")
        return {"event_id": event_id, "status": "completed"}

    def overview(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT event_id,job_id,status,attempts,last_error,created_at,delivered_at "
                "FROM automation_outbox ORDER BY created_at DESC LIMIT 100",
            ).fetchall()
            return [dict(row) for row in rows]

    def retry_failed(self, event_id):
        with self.connect() as connection:
            count = connection.execute(
                "UPDATE automation_outbox SET status='retry',attempts=0,next_attempt=0,"
                "lease=NULL,last_error=NULL WHERE event_id=? AND status='failed'", (event_id,),
            ).rowcount
        return bool(count)

    def reviews(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT event_id,job_id,payload,status,created_at,notified_at "
                "FROM automation_reviews ORDER BY created_at DESC LIMIT 100",
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]


class AutomationDispatcher:
    def __init__(self, store, url, token):
        self.store, self.url, self.token = store, url, token

    def deliver_one(self):
        if not self.url or not self.token:
            return False
        row = self.store.claim_delivery()
        if not row:
            return False
        error, permanent = None, False
        try:
            response = httpx.post(self.url, json=json.loads(row["payload"]),
                                  headers={"X-FaturaGuard-Token": self.token}, timeout=25,
                                  follow_redirects=False)
            if response.status_code in (400, 401, 403, 404, 410, 422):
                permanent = True
            response.raise_for_status()
            body = response.json()
            if body.get("event_id") != row["event_id"] or body.get("status") not in ("completed", "duplicate"):
                raise ValueError("ack")
        except httpx.HTTPStatusError as exc:
            error = f"http_{exc.response.status_code}"
        except (httpx.HTTPError, ValueError, AttributeError):
            error = "delivery_or_ack_failed"
        self.store.finish_delivery(row, error, permanent)
        return True
