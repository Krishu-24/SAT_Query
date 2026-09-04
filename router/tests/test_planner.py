from app.planner.planner import QueryPlanner
from app.schemas.task import TaskType


def test_planner_creates_single_task():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Describe this satellite image."
    )

    assert len(plan.tasks) == 1

    assert plan.tasks[0].task_id == "task_1"
    assert plan.tasks[0].task == TaskType.CAPTIONING
    assert plan.tasks[0].depends_on == []


def test_planner_creates_multiple_tasks():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Find the water bodies and describe the image."
    )

    assert len(plan.tasks) == 2

    assert plan.tasks[0].task_id == "task_1"
    assert plan.tasks[0].task == TaskType.GROUNDING

    assert plan.tasks[1].task_id == "task_2"
    assert plan.tasks[1].task == TaskType.CAPTIONING


def test_planner_tasks_are_independent_by_default():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Locate the roads and describe this satellite image."
    )

    assert len(plan.tasks) == 2

    assert plan.tasks[0].depends_on == []
    assert plan.tasks[1].depends_on == []


def test_planner_assigns_task_ids_in_order():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Find the buildings and describe the image."
    )

    assert [
        task.task_id
        for task in plan.tasks
    ] == [
        "task_1",
        "task_2",
    ]

def test_planner_creates_dependency_for_then():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Find the water bodies then describe the image."
    )

    assert len(plan.tasks) == 2

    assert plan.tasks[0].task_id == "task_1"
    assert plan.tasks[0].depends_on == []

    assert plan.tasks[1].task_id == "task_2"
    assert plan.tasks[1].depends_on == ["task_1"]


def test_planner_keeps_and_tasks_independent():

    planner = QueryPlanner()

    plan = planner.create_plan(
        "Find the water bodies and describe the image."
    )

    assert len(plan.tasks) == 2

    assert plan.tasks[0].depends_on == []
    assert plan.tasks[1].depends_on == []

def test_planner_falls_back_to_rule_based_classifier():

    planner = QueryPlanner()

    class FailingLLMPlanner:

        def create_plan(self, query: str):
            raise RuntimeError("LLM unavailable")

    planner.llm_planner = FailingLLMPlanner()

    plan = planner.create_plan(
        "Describe this satellite image."
    )

    assert len(plan.tasks) == 1
    assert plan.tasks[0].task.value == "CAPTIONING"