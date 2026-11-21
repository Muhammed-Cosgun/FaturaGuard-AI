"""FastAPI uygulama giriş noktası."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from faturaguard.config import Settings, settings
from faturaguard.services.agent_workflow import FaturaGuardAgent, SourceBackedAgent
from faturaguard.services.correction_workflow import CorrectionWorkflow
from faturaguard.services.document_chat import DocumentChat
from faturaguard.services.document_storage import DocumentStorage, FilePolicyError
from faturaguard.services.hybrid_retrieval import (
    Bm25LexicalRetriever,
    ChromaSemanticStore,
    HybridRetriever,
    SentenceTransformerEmbedder,
)
from faturaguard.services.n8n_webhook import N8nWebhookNotifier
from faturaguard.services.official_rag import OfficialRagIndex
from faturaguard.services.reporting import build_report_payload
from faturaguard.services.source_backed_explanation import (
    CohereStructuredGenerator,
    DeterministicCorrectionPlanGenerator,
    DeterministicSourceGenerator,
    FallbackCorrectionPlanGenerator,
    FallbackExplanationGenerator,
    GeminiCorrectionPlanGenerator,
    GeminiStructuredGenerator,
    GroqCorrectionPlanGenerator,
    GroqStructuredGenerator,
    LLMUnavailableError,
    OllamaStructuredGenerator,
)
from faturaguard.services.validation_adapter import EfaturaKontrolAdapter, ValidatorUnavailableError

PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
logger = logging.getLogger(__name__)


def format_turkey_time(value: str) -> str:
    """UTC audit zamanını arayüzde Türkiye yerel saatiyle gösterir."""

    return (
        datetime.fromisoformat(value)
        .astimezone(ZoneInfo("Europe/Istanbul"))
        .strftime("%d.%m.%Y %H:%M")
    )


templates.env.filters["turkey_time"] = format_turkey_time


def _select_explanation_generator(app_settings: Settings):
    """Yapılandırılmış açıklama için güvenli, test edilebilir sağlayıcı zincirini kurar."""

    local_generator = OllamaStructuredGenerator(
        app_settings.ollama_model, app_settings.ollama_base_url
    )
    deterministic_generator = DeterministicSourceGenerator()
    if app_settings.llm_provider == "local":
        return local_generator

    fallback_generator = deterministic_generator
    if app_settings.groq_api_key:
        fallback_generator = FallbackExplanationGenerator(
            GroqStructuredGenerator(
                app_settings.groq_api_key,
                app_settings.groq_model,
                timeout_seconds=app_settings.groq_timeout_seconds,
            ),
            deterministic_generator,
        )
    if app_settings.llm_provider == "cohere" and app_settings.cohere_api_key:
        return FallbackExplanationGenerator(
            CohereStructuredGenerator(
                app_settings.cohere_api_key,
                app_settings.cohere_model,
                timeout_seconds=app_settings.cohere_timeout_seconds,
            ),
            fallback_generator,
        )
    if app_settings.llm_provider != "groq" and app_settings.gemini_api_key:
        return FallbackExplanationGenerator(
            GeminiStructuredGenerator(
                app_settings.gemini_api_key,
                app_settings.gemini_model,
                timeout_seconds=app_settings.gemini_timeout_seconds,
            ),
            fallback_generator,
        )
    if app_settings.groq_api_key:
        return fallback_generator
    return local_generator


def _select_correction_planner(app_settings: Settings):
    """Maskeli XML patch planı için API sağlayıcısı ve güvenli fallback zinciri."""
    planner = DeterministicCorrectionPlanGenerator()
    if app_settings.groq_api_key:
        planner = FallbackCorrectionPlanGenerator(
            GroqCorrectionPlanGenerator(
                app_settings.groq_api_key,
                app_settings.groq_model,
                timeout_seconds=app_settings.correction_plan_timeout_seconds,
            ),
            planner,
        )
    if app_settings.gemini_api_key and app_settings.llm_provider != "groq":
        planner = FallbackCorrectionPlanGenerator(
            GeminiCorrectionPlanGenerator(
                app_settings.gemini_api_key,
                app_settings.gemini_model,
                timeout_seconds=app_settings.correction_plan_timeout_seconds,
            ),
            planner,
        )
    return planner


def _create_agent() -> SourceBackedAgent | None:
    chunks_path = settings.data_directory / "rag" / "official_gib_chunks.json"
    chroma_path = settings.data_directory / "chroma"
    if not chunks_path.is_file() or not chroma_path.exists():
        return None
    chunks = OfficialRagIndex.load(chunks_path).chunks
    retriever = HybridRetriever(
        ChromaSemanticStore(chroma_path, SentenceTransformerEmbedder()),
        Bm25LexicalRetriever(chunks),
    )
    return SourceBackedAgent(
        retriever,
        _select_explanation_generator(settings),
        _select_correction_planner(settings),
    )


@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """RAG soğuk başlangıcını ilk tıklama yerine sunucu açılışına taşır."""

    agent = app.state.source_backed_agent
    if agent is None:
        app.state.rag_warmup_status = "skipped"
    else:
        app.state.rag_warmup_status = "running"
        try:
            await asyncio.to_thread(agent.warmup)
        except Exception as error:  # Uygulama, ısıtma başarısız olsa da güvenle açılabilmeli.
            app.state.rag_warmup_status = "failed"
            logger.warning("RAG başlangıç ısıtması tamamlanamadı: %s", type(error).__name__)
        else:
            app.state.rag_warmup_status = "ready"
            logger.info("RAG başlangıç ısıtması tamamlandı.")
    try:
        yield
    finally:
        # Native Schematron nesneleri doğrulamanın çalıştığı event loop üzerinde
        # temizlenmeli; TestClient thread'i sonlandıktan sonraya bırakılmamalı.
        app.state.validator.close()


def create_app() -> FastAPI:
    """Bağımsız test edilebilir uygulama örneği oluşturur."""
    app = FastAPI(
        title=settings.application_name,
        version=settings.application_version,
        lifespan=application_lifespan,
    )
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    app.state.document_storage = DocumentStorage(settings.data_directory, settings.max_upload_bytes)
    app.state.validator = EfaturaKontrolAdapter()
    app.state.correction_workflow = CorrectionWorkflow(settings.data_directory, app.state.validator)
    app.state.source_backed_agent = _create_agent()
    app.state.workflow_agent = FaturaGuardAgent(app.state.source_backed_agent)
    app.state.n8n_notifier = N8nWebhookNotifier(settings.n8n_webhook_url)

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "version": settings.application_version}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "home.html")

    @app.get("/history", response_class=HTMLResponse, include_in_schema=False)
    def history(request: Request) -> HTMLResponse:
        jobs = app.state.correction_workflow.list_recent_jobs()
        return templates.TemplateResponse(request, "history.html", {"jobs": jobs})

    @app.post("/documents/validate", response_class=HTMLResponse, include_in_schema=False)
    async def validate_document(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
        filename = file.filename or ""
        contents = await file.read(settings.max_upload_bytes + 1)
        try:
            stored = app.state.document_storage.store_original(contents, filename)
            agent_result = app.state.workflow_agent.process_uploaded_document(
                stored, app.state.correction_workflow
            )
            job = agent_result["job"]
            if job is None:
                raise RuntimeError("Agent doğrulama işlemi kayıt oluşturamadı.")
            report = job.report
        except FilePolicyError as error:
            return templates.TemplateResponse(
                request, "validation_result.html", {"error": str(error)}, status_code=400
            )
        except ValidatorUnavailableError as error:
            return templates.TemplateResponse(
                request, "validation_result.html", {"error": str(error)}, status_code=503
            )
        finally:
            await file.close()

        return templates.TemplateResponse(
            request,
            "validation_result.html",
            {"stored": stored, "report": report, "job": job},
        )

    @app.post(
        "/jobs/{job_id}/proposals/{proposal_id}",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def decide_correction(
        request: Request, job_id: str, proposal_id: str, decision: str = Form(...)
    ) -> HTMLResponse:
        try:
            agent_result = app.state.workflow_agent.handle_correction_decision(
                app.state.correction_workflow, job_id, proposal_id, decision
            )
            job = agent_result["job"]
            if job is None:
                raise RuntimeError("Agent düzeltme işlemi sonuç üretmedi.")
        except (ValueError, OSError) as error:
            return templates.TemplateResponse(
                request, "validation_result.html", {"error": str(error)}, status_code=400
            )
        notification = app.state.n8n_notifier.notify(job)
        job = app.state.correction_workflow.record_automation_event(
            job.job_id, notification.status, notification.detail
        )
        return templates.TemplateResponse(
            request,
            "validation_result.html",
            {"report": job.report, "job": job},
        )

    @app.get("/jobs/{job_id}/report", response_class=HTMLResponse, include_in_schema=False)
    async def view_report(request: Request, job_id: str) -> HTMLResponse:
        try:
            job = app.state.correction_workflow._store.load(job_id)
        except OSError as error:
            return templates.TemplateResponse(
                request, "validation_result.html", {"error": str(error)}, status_code=404
            )
        return templates.TemplateResponse(
            request,
            "report.html",
            {
                "job": job,
                "payload": build_report_payload(job),
                "audit_events": app.state.correction_workflow.list_audit_events(job_id),
            },
        )

    @app.get("/jobs/{job_id}/report.json", include_in_schema=False)
    async def download_report(job_id: str) -> JSONResponse:
        job = app.state.correction_workflow._store.load(job_id)
        payload = build_report_payload(job)
        payload["audit_events"] = app.state.correction_workflow.list_audit_events(job_id)
        return JSONResponse(
            payload,
            headers={
                "Content-Disposition": f'attachment; filename="faturaguard-report-{job_id}.json"'
            },
        )

    @app.post(
        "/jobs/{job_id}/findings/{finding_code}/explain",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def explain_finding(request: Request, job_id: str, finding_code: str) -> HTMLResponse:
        if app.state.source_backed_agent is None:
            return templates.TemplateResponse(
                request,
                "validation_result.html",
                {"error": "GİB RAG indeksi hazır değil; önce kaynak indeksini oluşturun."},
                status_code=503,
            )
        try:
            job = app.state.workflow_agent.explain_finding(
                job_id, finding_code, app.state.correction_workflow
            )
        except (ValueError, LLMUnavailableError) as error:
            return templates.TemplateResponse(
                request, "validation_result.html", {"error": str(error)}, status_code=503
            )
        return templates.TemplateResponse(
            request,
            "validation_result.html",
            {"report": job.report, "job": job},
        )

    @app.post('/jobs/{job_id}/chat', include_in_schema=False)
    async def document_chat(
        request: Request, job_id: str,
        question: str = Form(..., min_length=1, max_length=600),
        finding_code: str = Form(''),
    ):
        wants_json = 'application/json' in request.headers.get('accept', '')
        try:
            job, turn = await asyncio.to_thread(
                app.state.correction_workflow.chat, job_id, question, finding_code,
                DocumentChat(app.state.source_backed_agent),
            )
        except (FileNotFoundError, ValueError) as error:
            status = 404 if isinstance(error, FileNotFoundError) else 400
            message = 'İşlem kaydı bulunamadı.' if status == 404 else str(error)
            if wants_json:
                return JSONResponse({'error': message}, status_code=status)
            return templates.TemplateResponse(
                request, 'validation_result.html', {'error': message}, status_code=status,
            )
        if wants_json:
            return JSONResponse({'turn': turn.model_dump(mode='json')})
        return templates.TemplateResponse(
            request, 'validation_result.html', {'report': job.report, 'job': job},
        )

    return app


app = create_app()
