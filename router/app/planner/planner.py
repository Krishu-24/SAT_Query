from app.router.classifier import QueryClassifier
from app.planner.llm_planner import LLMPlanner
from app.schemas.intent import QueryPlan


class QueryPlanner:

    def __init__(self):
        self.classifier = QueryClassifier()
        self.llm_planner = LLMPlanner()

    def create_plan(self, query: str) -> QueryPlan:

        try:
            plan = self.llm_planner.create_plan(query)

            self._apply_dependencies(plan, query)

            return plan

        except Exception:
            return self._create_rule_based_plan(query)

    def _apply_dependencies(
        self,
        plan: QueryPlan,
        query: str
    ) -> None:

        query_lower = query.lower()

        dependency_separators = [
            " then ",
            " after that ",
        ]

        has_dependency = any(
            separator in query_lower
            for separator in dependency_separators
        )

        if not has_dependency:
            for task in plan.tasks:
                task.depends_on = []

            return

        for index, task in enumerate(plan.tasks):

            if index == 0:
                task.depends_on = []
            else:
                task.depends_on = [
                    plan.tasks[index - 1].task_id
                ]

    def _create_rule_based_plan(
        self,
        query: str
    ) -> QueryPlan:
        # Share compound-VQA / grounding rules with QueryClassifier.create_plan
        plan = self.classifier.create_plan(query)
        for index, task in enumerate(plan.tasks, start=1):
            task.task_id = f"task_{index}"
        self._apply_dependencies(plan, query)
        return plan
