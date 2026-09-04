from pydantic import BaseModel, Field
from typing import List


class ImageInput(BaseModel):
    path: str = Field(
        description="Path to the satellite image"
    )

    modality: str = Field(
        description="Image modality, e.g. optical or SAR"
    )


class QueryRequest(BaseModel):
    query: str = Field(
        description="Natural-language user query"
    )

    images: List[ImageInput] = Field(
        description="Satellite images provided with the query"
    )