from app.agents.base import BaseAgent
from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class CaptioningPipeline(BaseAgent):

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return {
            "agent": "CAPTIONING_AGENT",
            "task": intent.task.value,
            "status": "success",
            "result": "Captioning pipeline received the image.",
            "images_processed": len(images),
        }