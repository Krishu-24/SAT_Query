from app.schemas.intent import QueryIntent
from app.schemas.task import TaskType
from app.planner.capabilities import Capability


def test_intent_derives_grounding_capability():

    intent = QueryIntent(
        task_id="task_1",
        task=TaskType.GROUNDING,
        confidence=0.95,
    )

    assert intent.capabilities == [
        Capability.SPATIAL_LOCALIZATION
    ]


def test_intent_derives_vqa_capability():

    intent = QueryIntent(
        task_id="task_1",
        task=TaskType.VQA,
        confidence=0.80,
    )

    assert intent.capabilities == [
        Capability.VISUAL_QUESTION_ANSWERING
    ]


def test_intent_preserves_explicit_capabilities():

    intent = QueryIntent(
        task_id="task_1",
        task=TaskType.VQA,
        capabilities=[
            Capability.VISUAL_QUESTION_ANSWERING
        ],
        confidence=0.80,
    )

    assert intent.capabilities == [
        Capability.VISUAL_QUESTION_ANSWERING
    ]