from enum import Enum

from app.schemas.task import TaskType


class Capability(str, Enum):
    VISUAL_QUESTION_ANSWERING = "visual_question_answering"
    SCENE_DESCRIPTION = "scene_description"
    SPATIAL_LOCALIZATION = "spatial_localization"
    CHANGE_ANALYSIS = "change_analysis"
    CROSS_MODAL_ANALYSIS = "cross_modal_analysis"


TASK_CAPABILITIES = {
    TaskType.VQA: [
        Capability.VISUAL_QUESTION_ANSWERING,
    ],

    TaskType.CAPTIONING: [
        Capability.SCENE_DESCRIPTION,
    ],

    TaskType.GROUNDING: [
        Capability.SPATIAL_LOCALIZATION,
    ],

    TaskType.CHANGE_DETECTION: [
        Capability.CHANGE_ANALYSIS,
    ],

    TaskType.CHANGE_VQA: [
        Capability.CHANGE_ANALYSIS,
        Capability.VISUAL_QUESTION_ANSWERING,
    ],

    TaskType.OPTICAL_SAR: [
        Capability.CROSS_MODAL_ANALYSIS,
    ],

    TaskType.UNKNOWN: [],
}


def get_capabilities(task: TaskType) -> list[Capability]:
    """
    Return the capabilities required by a task.
    """

    return TASK_CAPABILITIES.get(task, [])