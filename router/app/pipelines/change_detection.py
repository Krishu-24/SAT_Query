from app.agents.base import BaseAgent
from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class ChangeDetectionPipeline(BaseAgent):

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return {
            "agent": "CHANGE_DETECTION_AGENT",
            "task": intent.task.value,
            "status": "success",
            "result": "Change detection pipeline received the images.",
            "images_processed": len(images),
        }