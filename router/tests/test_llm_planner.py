import pytest

from app.planner.llm_planner import LLMPlanner
from app.schemas.task import TaskType


class FakeOllamaClient:

    def __init__(self, response: str):
        self.response = response

    def generate(
        self,
        prompt: str,
        response_schema=None,
    ) -> str:
        return self.response


def test_llm_planner_creates_valid_plan():

    response = """
    {
        "tasks": [
            {
                "task_id": "task_1",
                "task": "CHANGE_DETECTION",
                "target": null,
                "requires_spatial_evidence": false,
                "requires_segmentation": false,
                "requires_comparison": true,
                "depends_on": [],
                "confidence": 0.95
            }
        ]
    }
    """

    planner = LLMPlanner(
        client=FakeOllamaClient(response)
    )

    plan = planner.create_plan(
        "What changed between these two satellite images?"
    )

    assert len(plan.tasks) == 1
    assert plan.tasks[0].task == TaskType.CHANGE_DETECTION
    assert plan.tasks[0].requires_comparison is True


def test_llm_planner_derives_capabilities():

    response = """
    {
        "tasks": [
            {
                "task_id": "task_1",
                "task": "GROUNDING",
                "target": "buildings",
                "requires_spatial_evidence": true,
                "requires_segmentation": false,
                "requires_comparison": false,
                "depends_on": [],
                "confidence": 0.90
            }
        ]
    }
    """

    planner = LLMPlanner(
        client=FakeOllamaClient(response)
    )

    plan = planner.create_plan(
        "Locate the buildings in this satellite image."
    )

    assert plan.tasks[0].task == TaskType.GROUNDING
    assert plan.tasks[0].target == "buildings"
    assert len(plan.tasks[0].capabilities) == 1


def test_llm_planner_rejects_invalid_json():

    planner = LLMPlanner(
        client=FakeOllamaClient(
            "This is not JSON"
        )
    )

    with pytest.raises(ValueError, match="invalid query plan"):
        planner.create_plan(
            "Describe this image."
        )


def test_llm_planner_rejects_invalid_plan():

    response = """
    {
        "tasks": [
            {
                "task_id": "task_1",
                "task": "NOT_A_REAL_TASK",
                "confidence": 0.90
            }
        ]
    }
    """

    planner = LLMPlanner(
        client=FakeOllamaClient(response)
    )

    with pytest.raises(ValueError, match="invalid query plan"):
        planner.create_plan(
            "Do something with this image."
        )