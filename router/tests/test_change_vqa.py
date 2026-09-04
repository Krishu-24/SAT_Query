from app.agents.setup import create_agent_registry
from app.planner.capabilities import Capability


def test_registry_selects_change_vqa_agent():

    registry = create_agent_registry()

    agents = registry.find_agents([
        Capability.CHANGE_ANALYSIS,
        Capability.VISUAL_QUESTION_ANSWERING,
    ])

    assert agents == ["CHANGE_VQA_AGENT"]