from app.router.router import QueryRouter
from app.schemas.intent import QueryIntent, QueryPlan
from app.schemas.query import ImageInput


class QueryExecutor:

    def __init__(self, router: QueryRouter):
        self.router = router

    def execute(
        self,
        plan: QueryPlan,
        images: list[ImageInput]
    ) -> list[dict]:

        results = {}

        while len(results) < len(plan.tasks):

            progress = False

            for intent in plan.tasks:

                # Skip tasks that have already been executed.
                if intent.task_id in results:
                    continue

                # Check whether all dependencies are complete.
                dependencies_ready = all(
                    dependency in results
                    for dependency in intent.depends_on
                )

                if not dependencies_ready:
                    continue

                result = self.router.route(
                    intent,
                    images
                )

                results[intent.task_id] = result

                progress = True

            # Prevent an infinite loop if the plan contains
            # an invalid dependency or circular dependency.
            if not progress:
                raise ValueError(
                    "Unable to execute plan. "
                    "Unresolved or circular task dependencies."
                )

        # Return results in the same order as the plan.
        return [
            results[intent.task_id]
            for intent in plan.tasks
        ]