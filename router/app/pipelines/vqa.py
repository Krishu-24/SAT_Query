from app.agents.base import BaseAgent
from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class VQAPipeline(BaseAgent):

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return {
            "agent": "VQA_AGENT",
            "task": intent.task.value,
            "question": intent.target,
            "status": "success",
            "result": (
                f"VQA pipeline received question: "
                f"'{intent.target}'."
            ),
            "images_processed": len(images),
        }