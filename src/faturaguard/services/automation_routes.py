"""n8n callback'leri; XML, sohbet ve düzeltme uçlarını dışarı açmaz."""

import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class Completion(BaseModel):
    lease: str = Field(min_length=32, max_length=32, pattern=r"^[a-f0-9]+$")


def automation_router(store, token):
    router = APIRouter(prefix="/automation")

    def authorize(request):
        supplied = request.headers.get("X-FaturaGuard-Token", "")
        if not token or not secrets.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="Otomasyon yetkisi gerekli.")

    @router.get("/deliveries", include_in_schema=False)
    def deliveries(request: Request):
        authorize(request)
        return store.overview()

    @router.get("/reviews", include_in_schema=False)
    def reviews(request: Request):
        authorize(request)
        return store.reviews()

    @router.post("/reviews/{event_id}/claim", include_in_schema=False)
    def claim(event_id: str, request: Request):
        authorize(request)
        try:
            result = store.claim_review(event_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return JSONResponse(result, status_code=409 if result["status"] == "busy" else 200)

    @router.post("/reviews/{event_id}/complete", include_in_schema=False)
    def complete(event_id: str, body: Completion, request: Request):
        authorize(request)
        try:
            return store.complete_review(event_id, body.lease)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return router
