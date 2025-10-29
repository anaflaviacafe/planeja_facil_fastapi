from pydantic import BaseModel
from typing import List, Optional
from enum import IntEnum, Enum
from datetime import datetime

class DurationType(IntEnum):
    min = 0
    hours = 1
    days = 2

class StatusTypeOP(IntEnum):
    create = 0
    start = 1
    paused = 2
    end = 3

class PriorityType(IntEnum):
    baixa = 0
    normal = 1
    media = 2
    alta = 3
    urgente = 4
    
class PauseType(IntEnum):
    maintenance = 0
    resource = 1
    material = 2
    machine = 3
    other = 4

class BlockCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    templateId: str    
    durationType: DurationType

class PhaseCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    duration: float
    templateId: Optional[str] = None

class ResourceCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    code: Optional[str] = None
    type: Optional[str] = None
    templateId: str
    active: bool = True

class PhaseUpdateResource(BaseModel):
    resourceId: str

class OpModel(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    templateId: Optional[str] = None
    description: str
    code: str
    dateCreated: Optional[datetime] = None
    dateLimit: Optional[datetime] = None
    dateStart: Optional[datetime] = None
    dateEnd: Optional[datetime] = None
    status: Optional[StatusTypeOP] = StatusTypeOP.create
    priority: Optional[PriorityType] = PriorityType.normal
    estimatedDuration: Optional[float] = 0.0
    quantity: Optional[int] = 1
    progressPrc: Optional[int] = 0
    inProducing: Optional[bool] = False
    active: Optional[bool] = True
    block: Optional[BlockCreate] = None
    phase: Optional[PhaseCreate] = None
    resource: Optional[ResourceCreate] = None
    customColumn: Optional[str] = ""
    operatorName: Optional[str] = None

    class Config:
        orm_mode = True # Ensure this is imported or defined in models.py