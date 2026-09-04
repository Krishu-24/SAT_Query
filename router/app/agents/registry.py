from app.agents.base import BaseAgent
from app.planner.capabilities import Capability


class AgentRegistry:

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._capabilities: dict[str, set[Capability]] = {}

    def register(
        self,
        name: str,
        agent: BaseAgent,
        capabilities: list[Capability]
    ) -> None:

        self._agents[name] = agent
        self._capabilities[name] = set(capabilities)

    def get_agent(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def find_agents(
        self,
        required_capabilities: list[Capability]
    ) -> list[str]:

        required = set(required_capabilities)

        return [
            name
            for name, capabilities in self._capabilities.items()
            if required.issubset(capabilities)
        ]

    def select_agent(
        self,
        required_capabilities: list[Capability]
    ) -> str | None:

        required = set(required_capabilities)

        candidates = self.find_agents(required_capabilities)

        if not candidates:
            return None

        exact_matches = [
            name
            for name in candidates
            if self._capabilities[name] == required
        ]

        if exact_matches:
            return exact_matches[0]

        return min(
            candidates,
            key=lambda name: len(self._capabilities[name] - required)
        )