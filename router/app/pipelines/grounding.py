from app.agents.base import BaseAgent
from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class GroundingPipeline(BaseAgent):

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return {
            "agent": "GROUNDING_AGENT",
            "task": intent.task.value,
            "target": intent.target,
            "status": "success",
            "result": (
                f"Grounding pipeline received request to locate "
                f"'{intent.target}'."
            ),
            "images_processed": len(images),
        }