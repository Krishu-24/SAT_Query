from app.executor.executor import QueryExecutor
from app.schemas.intent import QueryIntent, QueryPlan
from app.schemas.task import TaskType
from app.router.router import QueryRouter
from app.planner.capabilities import Capability


class MockRouter:

    def __init__(self):
        self.execution_order = []

    def route(self, intent, images):

        self.execution_order.append(
            intent.task_id
        )

        return {
            "task_id": intent.task_id,
            "status": "success"
        }


def test_executor_runs_independent_tasks():

    router = MockRouter()
    executor = QueryExecutor(router)

    plan = QueryPlan(
        tasks=[
            QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                depends_on=[],
                confidence=0.9,
            ),
            QueryIntent(
                task_id="task_2",
                task=TaskType.CAPTIONING,
                depends_on=[],
                confidence=0.9,
            ),
        ]
    )

    results = executor.execute(
        plan,
        []
    )

    assert router.execution_order == [
        "task_1",
        "task_2",
    ]

    assert len(results) == 2


def test_executor_respects_dependencies():

    router = MockRouter()
    executor = QueryExecutor(router)

    plan = QueryPlan(
        tasks=[
            QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                depends_on=[],
                confidence=0.9,
            ),
            QueryIntent(
                task_id="task_2",
                task=TaskType.VQA,
                depends_on=["task_1"],
                confidence=0.9,
            ),
        ]
    )

    results = executor.execute(
        plan,
        []
    )

    assert router.execution_order == [
        "task_1",
        "task_2",
    ]

    assert len(results) == 2


def test_executor_detects_circular_dependency():

    router = MockRouter()
    executor = QueryExecutor(router)

    plan = QueryPlan(
        tasks=[
            QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                depends_on=["task_2"],
                confidence=0.9,
            ),
            QueryIntent(
                task_id="task_2",
                task=TaskType.VQA,
                depends_on=["task_1"],
                confidence=0.9,
            ),
        ]
    )

    try:
        executor.execute(plan, [])
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "circular task dependencies" in str(error)

def test_executor_works_with_real_router():

    router = QueryRouter()
    executor = QueryExecutor(router)

    plan = QueryPlan(
        tasks=[
            QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                target="water bodies",
                capabilities=[
        Capability.SPATIAL_LOCALIZATION],
                depends_on=[],
                confidence=0.9,
            ),
            QueryIntent(
                task_id="task_2",
                task=TaskType.CAPTIONING,
                target="image",
                capabilities=[
        Capability.SCENE_DESCRIPTION],
                depends_on=[],
                confidence=0.9,
            ),
        ]
    )

    results = executor.execute(
        plan,
        []
    )

    assert len(results) == 2

    assert results[0]["agent"] == "GROUNDING_AGENT"
    assert results[0]["status"] == "success"

    assert results[1]["agent"] == "CAPTIONING_AGENT"
    assert results[1]["status"] == "success"