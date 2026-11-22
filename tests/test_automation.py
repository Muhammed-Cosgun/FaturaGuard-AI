import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from faturaguard.domain.correction import CorrectionJob, CorrectionProposal
from faturaguard.domain.validation import ValidationReport, ValidationSummary
from faturaguard.services.automation import AutomationDispatcher, AutomationStore, correction_event
from faturaguard.services.automation_routes import automation_router
from faturaguard.services.correction_workflow import CorrectionWorkflow
from faturaguard.services.job_repository import SqliteCorrectionJobStore


@pytest.fixture
def queued(tmp_path):
    report = ValidationReport(original_filename="private-name.xml", findings=[],
                              summary=ValidationSummary(is_valid=True, error_count=0,
                                  warning_count=0, info_count=1, duration_ms=1))
    job = CorrectionJob(job_id="demo", original_filename="private-name.xml",
                        original_path="private/original.xml", original_sha256="old",
                        corrected_sha256="new", report=report, corrected_report=report,
                        proposals=[CorrectionProposal(proposal_id="p", rule_id="rule",
                            finding_code="finding", title="title", rationale="rationale",
                            target_path="path", before="1", after="2", status="applied")])
    jobs = SqliteCorrectionJobStore(tmp_path)
    event = correction_event(job)
    jobs.save(job, automation_event=event)
    return AutomationStore(tmp_path), job, event


def test_event_contains_only_bounded_summary_and_is_stable(queued):
    store, job, event = queued
    assert event == correction_event(job)
    text = json.dumps(event)
    for private in (job.original_filename, job.original_path, "<Invoice", "chat_history", "before"):
        assert private not in text
    assert store.overview()[0]["status"] == "pending"
    job.proposals[0].status = "rejected"
    assert correction_event(job) is None
    job.proposals[0].status = "applied"
    job.corrected_report = None
    assert correction_event(job) is None


def test_job_and_event_are_one_transaction_and_duplicate_save_does_not_duplicate(queued, tmp_path):
    store, job, event = queued
    jobs = SqliteCorrectionJobStore(tmp_path)
    jobs.save(job, automation_event=event)
    assert len(store.overview()) == 1
    job.original_filename = "must-not-persist.xml"
    with pytest.raises(KeyError):
        jobs.save(job, automation_event={"event_id": "incomplete"})
    assert jobs.load(job.job_id).original_filename == "private-name.xml"


def test_restart_concurrent_claim_and_stale_worker_cannot_overwrite(queued, tmp_path):
    store, _, event = queued
    with ThreadPoolExecutor(4) as executor:
        claimed = list(executor.map(lambda _: AutomationStore(tmp_path).claim_delivery(now=1), range(4)))
    rows = [row for row in claimed if row]
    assert len(rows) == 1
    assert AutomationStore(tmp_path).claim_delivery(now=180) is None
    fresh = store.claim_delivery(now=182)
    assert fresh["attempts"] == 2
    store.finish_delivery(rows[0], now=183)
    assert store.overview()[0]["status"] == "sending"
    store.finish_delivery(fresh, now=184)
    assert store.overview()[0]["status"] == "delivered"
    assert store.claim_review(event["event_id"])["should_notify"]


def test_review_is_unique_and_expired_lease_can_retry(queued):
    store, _, event = queued
    first = store.claim_review(event["event_id"], now=1)
    assert store.claim_review(event["event_id"], now=2)["status"] == "busy"
    new = store.claim_review(event["event_id"], now=122)
    with pytest.raises(ValueError):
        store.complete_review(event["event_id"], first["lease"])
    store.complete_review(event["event_id"], new["lease"])
    assert store.claim_review(event["event_id"])["status"] == "duplicate"
    with store.connect() as connection:
        assert connection.execute("SELECT count(*) FROM automation_reviews").fetchone()[0] == 1


@pytest.mark.parametrize("code,expected", [(401, "failed"), (404, "failed"), (429, "retry"), (503, "retry")])
def test_http_errors_are_classified_and_do_not_store_sensitive_url(queued, monkeypatch, code, expected):
    store, _, _ = queued
    url = "https://example.test/private-secret-webhook"
    monkeypatch.setattr("faturaguard.services.automation.httpx.post", lambda *a, **kw:
        httpx.Response(code, request=httpx.Request("POST", url)))
    assert AutomationDispatcher(store, url, "token").deliver_one()
    row = store.overview()[0]
    assert row["status"] == expected and row["last_error"] == f"http_{code}"
    assert "secret" not in str(row)


def test_positive_http_without_business_ack_is_not_delivery(queued, monkeypatch):
    store, _, _ = queued
    monkeypatch.setattr("faturaguard.services.automation.httpx.post", lambda *a, **kw:
        httpx.Response(200, json={"message": "Workflow started"}, request=httpx.Request("POST", a[0])))
    AutomationDispatcher(store, "http://localhost/webhook", "token").deliver_one()
    assert store.overview()[0]["status"] == "retry"


def test_backoff_exhaustion_and_disabled_sender(queued):
    store, _, _ = queued
    assert not AutomationDispatcher(store, None, None).deliver_one()
    assert store.overview()[0]["attempts"] == 0
    now = 1
    for _ in range(6):
        row = store.claim_delivery(now=now)
        store.finish_delivery(row, "transport", now=now)
        assert store.claim_delivery(now=now + 1) is None
        now += 1000
    assert store.overview()[0]["status"] == "failed"


def test_last_attempt_crash_does_not_stay_sending_forever(queued):
    store, _, _ = queued
    for now in range(0, 1080, 180):
        store.claim_delivery(now=now)
    assert store.claim_delivery(now=1080) is None
    assert store.overview()[0]["status"] == "failed"


def test_callback_auth_and_unknown_event(queued):
    store, _, event = queued
    app = FastAPI()
    app.include_router(automation_router(store, "t" * 32))
    with TestClient(app) as client:
        path = f"/automation/reviews/{event['event_id']}"
        assert client.post(path + "/claim").status_code == 401
        headers = {"X-FaturaGuard-Token": "t" * 32}
        assert client.post("/automation/reviews/unknown/claim", headers=headers).status_code == 404
        first = client.post(path + "/claim", headers=headers).json()
        assert client.post(path + "/claim", headers=headers).status_code == 409
        assert client.post(path + "/complete", headers=headers, json={"lease": "x"}).status_code == 422
        assert client.post(path + "/complete", headers=headers, json={"lease": first["lease"]}).status_code == 200
        assert client.post(path + "/claim", headers=headers).json()["status"] == "duplicate"
        assert client.get("/automation/reviews").status_code == 401
        records = client.get("/automation/reviews", headers=headers).json()
        assert len(records) == 1 and records[0]["status"] == "notified"
        assert "lease" not in records[0] and "private-name" not in str(records)
        assert client.get("/jobs/demo/report").status_code == 404


def test_lost_ack_after_notification_does_not_resend_in_normal_recovery(queued, monkeypatch):
    store, _, event = queued
    messages = []

    def fake_n8n(url, **kwargs):
        review = store.claim_review(kwargs["json"]["event_id"])
        if review["should_notify"]:
            messages.append(review["message"])
            store.complete_review(event["event_id"], review["lease"])
            raise httpx.ReadTimeout("lost response")
        return httpx.Response(200, json=review, request=httpx.Request("POST", url))

    monkeypatch.setattr("faturaguard.services.automation.httpx.post", fake_n8n)
    dispatcher = AutomationDispatcher(store, "http://localhost/webhook", "token")
    dispatcher.deliver_one()
    assert store.overview()[0]["status"] == "retry"
    with store.connect() as connection:
        connection.execute("UPDATE automation_outbox SET next_attempt=0")
    dispatcher.deliver_one()
    assert len(messages) == 1 and store.overview()[0]["status"] == "delivered"


def test_actual_correction_enqueues_but_rejection_does_not(queued, tmp_path):
    store, job, _ = queued
    # Isolated minimal arithmetic invoice; no network, LLM or native validator.
    xml = b'''<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
      xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
      xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
      <cac:InvoiceLine><cbc:LineExtensionAmount>15.15</cbc:LineExtensionAmount></cac:InvoiceLine>
      <cac:LegalMonetaryTotal><cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount></cac:LegalMonetaryTotal>
      </Invoice>'''
    source = tmp_path / "original.xml"
    source.write_bytes(xml)
    job.job_id = "actual"
    job.original_path = str(source)
    job.corrected_report = None
    job.corrected_sha256 = None
    job.proposals[0] = CorrectionProposal(proposal_id="fix", rule_id="recalculate-line-extension-total",
        finding_code="hesap-dip-satir", title="Total", rationale="Total",
        target_path="cac:LegalMonetaryTotal/cbc:LineExtensionAmount", before="10.00", after="15.15")
    validator = type("Validator", (), {"validate": lambda self, *args: job.report})()
    workflow = CorrectionWorkflow(tmp_path, validator)
    workflow._store.save(job)
    updated = workflow.decide(job.job_id, "fix", "approve")
    assert updated.corrected_report and source.read_bytes() == xml
    assert len(store.overview()) == 2
    job.job_id = "rejected"
    workflow._store.save(job)
    workflow.decide(job.job_id, "fix", "reject")
    assert len(store.overview()) == 2


def test_workflow_failure_rolls_back_event_insertion(queued):
    store, _, _ = queued
    with pytest.raises(sqlite3.IntegrityError), store.connect() as connection:
        connection.execute("INSERT INTO automation_outbox(event_id) VALUES('invalid')")
    assert len(store.overview()) == 1


def test_manual_retry_only_releases_failed_events(queued):
    store, _, event = queued
    assert not store.retry_failed(event["event_id"])
    row = store.claim_delivery(now=1)
    store.finish_delivery(row, "http_401", permanent=True, now=1)
    assert store.retry_failed(event["event_id"])
    fresh = store.claim_delivery(now=2)
    assert fresh["attempts"] == 1
    store.finish_delivery(fresh, now=2)
    assert not store.retry_failed(event["event_id"])


def test_concurrent_review_requests_create_one_notification_owner(queued):
    store, _, event = queued
    with ThreadPoolExecutor(4) as executor:
        claims = list(executor.map(lambda _: store.claim_review(event["event_id"]), range(4)))
    assert sum(claim["should_notify"] for claim in claims) == 1


def test_callback_disabled_without_token(queued):
    store, _, event = queued
    app = FastAPI()
    app.include_router(automation_router(store, None))
    with TestClient(app) as client:
        assert client.get("/automation/deliveries").status_code == 401
        assert client.post(f"/automation/reviews/{event['event_id']}/claim").status_code == 401
