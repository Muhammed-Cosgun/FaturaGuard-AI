"""Docker içindeki n8n için yalnızca yetkili otomasyon rotalarını açar."""

from fastapi import FastAPI

from faturaguard.config import settings
from faturaguard.services.automation import AutomationStore
from faturaguard.services.automation_routes import automation_router

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(automation_router(AutomationStore(settings.data_directory), settings.automation_token))
