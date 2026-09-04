from pydantic import BaseModel, Field

from app.schemas.task import TaskType
from app.planner.capabilities import Capability
from app.planner.capabilities import get_capabilities


class QueryIntent(BaseModel):
    task_id: str

    task: TaskType

    target: str | None = None

    capabilities: list[Capability] = Field(
        default_factory=list
    )

    requires_spatial_evidence: bool = False

    requires_segmentation: bool = False

    requires_comparison: bool = False

    depends_on: list[str] = Field(
        default_factory=list
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    def model_post_init(self, __context) -> None:
        if not self.capabilities:
            self.capabilities = get_capabilities(
                self.task
            )


class QueryPlan(BaseModel):
    tasks: list[QueryIntent]