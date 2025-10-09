from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, time

""" Users """

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class ChildCreate(BaseModel):
    name: str
    email: str
    password: str

#  refresh token
class RefreshTokenRequest(BaseModel):
    refresh_token: str

""" Template """

class DateTable(BaseModel):
    date: datetime
    name: str

class Holidays(BaseModel):
    holidays: List[DateTable]

class Shift(BaseModel):
    entry: str
    exit: str

class TemplateModel(BaseModel):
    id: Optional[str] = None
    name: str
    holidays: Holidays
    holidayListName: Optional[str] = None
    weekStart: int   # 0 = sunday, ..., 6 = saturday
    weekEnd: int    
    shifts: List[Shift]
    user_id: Optional[str] = None  # for link main user

    class Config:
        arbitrary_types_allowed = True  # Allows custom types if needed
        exclude = {"id", "user_id"}  # Automatically excludes id and user_id on serialization


""" Resources  Types"""
class ResourceTypeCreate(BaseModel):
    name: str

# Pydantic model for updating/deleting (if needed)
class ResourceTypeUpdate(BaseModel):
    name: str

# Default resource types
DEFAULT_RESOURCE_TYPES = ['Humano', 'Local', 'Máquina', 'Próprio']