from app.agents.registry import AgentRegistry
from app.agents.base import BaseAgent
from app.planner.capabilities import Capability
from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class TestAgent(BaseAgent):

    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:
        return {
            "status": "success"
        }


def test_registry_finds_agent_with_required_capability():

    registry = AgentRegistry()

    registry.register(
        name="TEST_GROUNDING_AGENT",
        agent=TestAgent(),
        capabilities=[
            Capability.SPATIAL_LOCALIZATION
        ]
    )

    agents = registry.find_agents(
        [Capability.SPATIAL_LOCALIZATION]
    )

    assert agents == ["TEST_GROUNDING_AGENT"]


def test_registry_returns_empty_when_capability_is_missing():

    registry = AgentRegistry()

    registry.register(
        name="TEST_GROUNDING_AGENT",
        agent=TestAgent(),
        capabilities=[
            Capability.SPATIAL_LOCALIZATION
        ]
    )

    agents = registry.find_agents(
        [Capability.CHANGE_ANALYSIS]
    )

    assert agents == []

def test_registry_selects_most_specific_agent():

    registry = AgentRegistry()

    registry.register(
        name="VQA_AGENT",
        agent=TestAgent(),
        capabilities=[
            Capability.VISUAL_QUESTION_ANSWERING
        ]
    )

    registry.register(
        name="CHANGE_VQA_AGENT",
        agent=TestAgent(),
        capabilities=[
            Capability.CHANGE_ANALYSIS,
            Capability.VISUAL_QUESTION_ANSWERING
        ]
    )

    selected = registry.select_agent([
        Capability.CHANGE_ANALYSIS,
        Capability.VISUAL_QUESTION_ANSWERING
    ])

    assert selected == "CHANGE_VQA_AGENT"