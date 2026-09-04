from app.schemas.intent import QueryIntent
from app.agents.setup import create_agent_registry


class QueryRouter:

    def __init__(self):
        self.registry = create_agent_registry()

    def route(
        self,
        intent: QueryIntent,
        images
    ) -> dict:

        agent_name = self.registry.select_agent(
            intent.capabilities
        )

        if agent_name is None:
            return {
                "agent": "NO_AGENT",
                "task": intent.task.value,
                "status": "unsupported",
                "result": "No agent supports the required capabilities."
            }

        agent = self.registry.get_agent(agent_name)

        return agent.run(
            intent,
            images
        )