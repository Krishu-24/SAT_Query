from app.router.router import QueryRouter
from app.schemas.intent import QueryIntent
from app.schemas.task import TaskType
from app.planner.capabilities import Capability


def test_router_selects_grounding_agent():

    router = QueryRouter()

    intent = QueryIntent(
        task_id="task_1",
        task=TaskType.GROUNDING,
        target="water bodies",
        capabilities=[
            Capability.SPATIAL_LOCALIZATION
        ],
        requires_spatial_evidence=True,
        confidence=0.95,
    )

    result = router.route(intent, [])

    assert result["agent"] == "GROUNDING_AGENT"
    assert result["status"] == "success"


def test_router_selects_vqa_agent():

    router = QueryRouter()

    intent = QueryIntent(
        task_id="task_1",
        task=TaskType.VQA,
        target="What is the dominant land cover?",
        capabilities=[
            Capability.VISUAL_QUESTION_ANSWERING
        ],
        confidence=0.80,
    )

    result = router.route(intent, [])

    assert result["agent"] == "VQA_AGENT"
    assert result["status"] == "success"