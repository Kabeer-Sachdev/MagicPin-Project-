from __future__ import annotations

from fastapi import APIRouter
from app.schemas import MetadataResponse

router = APIRouter()


@router.get("/v1/metadata", response_model=MetadataResponse)
async def get_metadata():
    return MetadataResponse(
        team_name="Magicpin Vera AI Baseline",
        team_members=["Candidate"],
        model="deterministic-rules-v1",
        approach="Deterministic 4-context signal extraction with category strategy grounding and zero-hallucination composition",
        contact_email="candidate@example.com",
        version="1.0.0",
        submitted_at="2026-09-26T00:00:00Z"
    )
