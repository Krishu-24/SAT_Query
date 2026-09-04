from app.agents.registry import AgentRegistry
from app.agents.specialist_agents import (
    VQAAgent,
    GroundingAgent,
    CaptioningAgent,
    ChangeDetectionAgent,
    ChangeVQAAgent,
)

from app.planner.capabilities import Capability


def create_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()

    registry.register(
        name="VQA_AGENT",
        agent=VQAAgent(),
        capabilities=[
            Capability.VISUAL_QUESTION_ANSWERING
        ],
    )

    registry.register(
        name="GROUNDING_AGENT",
        agent=GroundingAgent(),
        capabilities=[
            Capability.SPATIAL_LOCALIZATION
        ],
    )

    registry.register(
        name="CAPTIONING_AGENT",
        agent=CaptioningAgent(),
        capabilities=[
            Capability.SCENE_DESCRIPTION
        ],
    )

    registry.register(
        name="CHANGE_DETECTION_AGENT",
        agent=ChangeDetectionAgent(),
        capabilities=[
            Capability.CHANGE_ANALYSIS
        ],
    )

    registry.register(
        name="CHANGE_VQA_AGENT",
        agent=ChangeVQAAgent(),
        capabilities=[
            Capability.CHANGE_ANALYSIS,
            Capability.VISUAL_QUESTION_ANSWERING,
        ],
    )

    return registry