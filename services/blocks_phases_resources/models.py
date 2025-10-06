from pydantic import BaseModel
from typing import List, Optional

class BlockCreate(BaseModel):
    name: str
    description: str
    templateName: Optional[str] = None

class PhaseCreate(BaseModel):
    name: str
    description: str
    duration: float
    templateName: Optional[str] = None

class ResourceCreate(BaseModel):
    name: str
    description: str
    code: Optional[str] = None
    type: Optional[str] = None
    templateName: Optional[str] = None
    active: bool = True

class PhaseUpdateResource(BaseModel):
    resourceId: str