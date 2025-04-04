from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

class CharacterBase(BaseModel):
    description: str
    name: Optional[str] = None

class CharacterCreate(CharacterBase):
    pass

class ImageVariation(BaseModel):
    image_path: str
    pose: Optional[str] = None
    expression: Optional[str] = None
    setting: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

class Character(CharacterBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)  # Timestamp for updates
    base_image_path: Optional[str] = None
    image_seed: Optional[int] = None  # Store the seed used for image generation
    variations: List[ImageVariation] = [] 