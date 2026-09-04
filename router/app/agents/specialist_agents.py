from app.agents.base import BaseAgent

from app.pipelines.vqa import VQAPipeline
from app.pipelines.grounding import GroundingPipeline
from app.pipelines.captioning import CaptioningPipeline
from app.pipelines.change_detection import ChangeDetectionPipeline

from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class VQAAgent(BaseAgent):

    def __init__(self):
        self.pipeline = VQAPipeline()

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return self.pipeline.run(intent, images)


class GroundingAgent(BaseAgent):

    def __init__(self):
        self.pipeline = GroundingPipeline()

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return self.pipeline.run(intent, images)


class CaptioningAgent(BaseAgent):

    def __init__(self):
        self.pipeline = CaptioningPipeline()

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return self.pipeline.run(intent, images)


class ChangeDetectionAgent(BaseAgent):

    def __init__(self):
        self.pipeline = ChangeDetectionPipeline()

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        return self.pipeline.run(intent, images)

class ChangeVQAAgent(BaseAgent):

    def __init__(self):
        self.change_pipeline = ChangeDetectionPipeline()
        self.vqa_pipeline = VQAPipeline()

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:

        change_result = self.change_pipeline.run(
            intent,
            images
        )

        vqa_result = self.vqa_pipeline.run(
            intent,
            images
        )

        return {
            "agent": "CHANGE_VQA_AGENT",
            "task": intent.task.value,
            "status": "success",
            "change_analysis": change_result,
            "visual_question_answering": vqa_result,
        }