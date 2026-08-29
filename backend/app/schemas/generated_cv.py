from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.graphs.nodes.cvtailor import TailoredCVContent
from app.models.enums import ContentLanguage


class GeneratedCVRenderRequest(BaseModel):
    job_id: UUID
    selected_pool_item_ids: list[UUID] = Field(default_factory=list)
    tailored_cv: TailoredCVContent
    ats_score: float | None = Field(default=None, ge=0.0, le=100.0)


class GeneratedCVResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    selected_pool_item_ids: list[UUID]
    output_language: ContentLanguage
    typst_source: str | None
    pdf_path: str | None
    ats_score: float | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
