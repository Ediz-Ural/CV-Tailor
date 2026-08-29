from pydantic import BaseModel


class PoolGraphTriggerResponse(BaseModel):
    queued: bool
    include_github: bool
    has_pdf: bool
