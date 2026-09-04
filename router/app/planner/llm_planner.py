from app.planner.llm import OllamaClient
from app.planner.prompt import build_planning_prompt
from app.schemas.intent import QueryPlan


class LLMPlanner:

    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient()

    def create_plan(self, query: str) -> QueryPlan:

        prompt = build_planning_prompt(query)

        response = self.client.generate(
            prompt,
            response_schema=QueryPlan,
        )

        try:
            return QueryPlan.model_validate_json(response)

        except Exception as exc:
            raise ValueError(
                "LLM returned an invalid query plan."
            ) from exc