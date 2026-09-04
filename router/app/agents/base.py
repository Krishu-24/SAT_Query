from abc import ABC, abstractmethod

from app.schemas.intent import QueryIntent
from app.schemas.query import ImageInput


class BaseAgent(ABC):

    @abstractmethod
    def run(
        self,
        intent: QueryIntent,
        images: list[ImageInput]
    ) -> dict:
        """
        Execute the specialist agent.

        Every specialist agent must implement this method.
        """
        pass