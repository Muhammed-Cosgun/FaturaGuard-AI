from faturaguard.domain.correction import CorrectionJob
from faturaguard.domain.validation import ValidationReport, ValidationSummary
from faturaguard.services.job_repository import SqliteCorrectionJobStore


def _job() -> CorrectionJob:
    return CorrectionJob(
        job_id="job-1",
        original_filename="ornek.xml",
        original_path="private/original.xml",
        original_sha256="original-hash",
        report=ValidationReport(
            original_filename="ornek.xml",
            summary=ValidationSummary(
                is_valid=True, error_count=0, warning_count=0, info_count=0, duration_ms=1
            ),
            findings=[],
        ),
    )


def test_sqlite_store_persists_job_audit_events_and_external_diff(tmp_path) -> None:
    store = SqliteCorrectionJobStore(tmp_path)
    job = _job()
    job.diff = "--- original.xml\n+++ corrected.xml\n-<Invoice/>\n+<Invoice><ID>1</ID></Invoice>"
    job.diff_path = str(store.store_diff(job.job_id, job.diff))

    store.save(job)
    store.append_event(job.job_id, "job_created", {"filename": job.original_filename})

    reloaded = SqliteCorrectionJobStore(tmp_path).load(job.job_id)

    assert reloaded.diff == job.diff
    assert reloaded.diff_path == job.diff_path
    assert store.list_events(job.job_id)[0]["event_type"] == "job_created"
    assert store.list_recent()[0]["original_filename"] == "ornek.xml"
    assert "<Invoice" not in (tmp_path / "faturaguard.sqlite3").read_bytes().decode(
        "latin-1", errors="ignore"
    )


def test_history_uses_revalidation_without_overwriting_original_report(tmp_path):
    store = SqliteCorrectionJobStore(tmp_path)
    job = _job()
    job.report.summary.warning_count = 2
    store.save(job)
    assert store.list_recent()[0]['current_report']['summary']['warning_count'] == 2
    assert not store.list_recent()[0]['has_correction']
    job.corrected_report = job.report.model_copy(deep=True)
    job.corrected_report.summary.warning_count = 0
    store.save(job)
    item = store.list_recent()[0]
    assert item['current_report']['summary']['warning_count'] == 0
    assert item['report']['summary']['warning_count'] == 2
    assert item['has_correction']
