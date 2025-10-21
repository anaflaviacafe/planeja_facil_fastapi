from pydantic import BaseModel
from typing import List, Optional
from enum import IntEnum

class DurationType(IntEnum):
    min = 0
    hours = 1
    days = 2

class BlockCreate(BaseModel):
    name: str
    description: str
    durationType: DurationType
    templateId: str

class PhaseCreate(BaseModel):
    name: str
    description: str
    duration: float
    templateId: Optional[str] = None

class ResourceCreate(BaseModel):
    name: str
    description: str
    code: Optional[str] = None
    type: Optional[str] = None
    templateId: str
    active: bool = True

class PhaseUpdateResource(BaseModel):
    resourceId: str

