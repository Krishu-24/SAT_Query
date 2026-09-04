from app.planner.capabilities import (
    Capability,
    get_capabilities,
)
from app.schemas.intent import TaskType


tasks = [
    TaskType.VQA,
    TaskType.GROUNDING,
    TaskType.CAPTIONING,
    TaskType.CHANGE_DETECTION,
    TaskType.CHANGE_VQA,
    TaskType.OPTICAL_SAR,
]


for task in tasks:

    capabilities = get_capabilities(task)

    print("\nTASK:")
    print(task.value)

    print("CAPABILITIES:")
    print([capability.value for capability in capabilities])

