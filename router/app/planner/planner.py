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

        query_lower = query.lower().strip()

        separators = [
            " and ",
            " also ",
            " then ",
            " as well as ",
            " along with ",
        ]

        parts = [query]
        dependency_mode = False

        for separator in separators:

            if separator in query_lower:

                split_index = query_lower.find(separator)

                left = query[
                    :split_index
                ].strip()

                right = query[
                    split_index + len(separator):
                ].strip()

                if left and right:
                    parts = [left, right]
                    dependency_mode = (
                        separator == " then "
                    )
                    break

        tasks = []

        for index, part in enumerate(
            parts,
            start=1
        ):

            intent = self.classifier.classify(part)

            if intent.task.value != "UNKNOWN":

                intent.task_id = f"task_{index}"

                if dependency_mode and index > 1:
                    intent.depends_on = [
                        "task_1"
                    ]

                tasks.append(intent)

        if not tasks:

            intent = self.classifier.classify(query)

            intent.task_id = "task_1"

            tasks.append(intent)

        return QueryPlan(tasks=tasks)