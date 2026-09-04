import json
from urllib.request import Request, urlopen

from pydantic import BaseModel


class OllamaClient:

    def __init__(
        self,
        model: str = "qwen3:4b-instruct",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url

    def generate(
        self,
        prompt: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if response_schema is not None:
            payload["format"] = response_schema.model_json_schema()

        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        with urlopen(request) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        return result["response"]