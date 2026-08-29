from uuid import UUID

from pydantic import BaseModel

from app.schemas.job import JobCreate
from app.services.cv_progress import CVGenerationProgress


class CVGenerationStartRequest(JobCreate):
    pass


class CVGenerationStartResponse(BaseModel):
    pipeline_id: UUID
    status: str
    status_url: str


class CVGenerationStatusResponse(CVGenerationProgress):
    pass
