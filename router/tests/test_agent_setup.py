from app.agents.setup import create_agent_registry
from app.planner.capabilities import Capability


def test_agent_setup_registers_vqa_agent():
    registry = create_agent_registry()

    agents = registry.find_agents([
        Capability.VISUAL_QUESTION_ANSWERING
    ])

    assert "VQA_AGENT" in agents


def test_agent_setup_registers_grounding_agent():
    registry = create_agent_registry()

    agents = registry.find_agents([
        Capability.SPATIAL_LOCALIZATION
    ])

    assert agents == ["GROUNDING_AGENT"]


def test_agent_setup_registers_captioning_agent():
    registry = create_agent_registry()

    agents = registry.find_agents([
        Capability.SCENE_DESCRIPTION
    ])

    assert agents == ["CAPTIONING_AGENT"]


def test_agent_setup_registers_change_detection_agent():
    registry = create_agent_registry()

    agents = registry.find_agents([
        Capability.CHANGE_ANALYSIS
    ])

    assert "CHANGE_DETECTION_AGENT" in agents