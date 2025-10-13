from pydantic import BaseModel, validator
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
    date: str
    name: str

    @validator('date', pre=True)
    def parse_date(cls, value):
        if isinstance(value, datetime):
            return value.isoformat()  # Convert datetime to ISO 8601 string
        return value

class Holidays(BaseModel):
    holidays: List[DateTable]

class Shift(BaseModel):
    entry: str = "" # string  "HH:mm:ss"
    exit: str = ""
class DateTableModel(BaseModel):
    date: str = ""
    name: str = ""
class HolidaysModel(BaseModel):
    holidays: List[DateTableModel]    

class TemplateModel(BaseModel):
    id: Optional[str] = None
    name: str
    #holidays: Optional[HolidaysWrapper] = HolidaysWrapper(holidays=[])
    holidays: HolidaysModel
    holidayListName: Optional[str] = None
    weekStart: int   # 0 = sunday, ..., 6 = saturday
    weekEnd: int    
    shifts: List[Shift]
    user_id: Optional[str] = None  # for link main user


""" Resources  Types"""
class ResourceTypeCreate(BaseModel):
    name: str

# Pydantic model for updating/deleting (if needed)
class ResourceTypeUpdate(BaseModel):
    name: str

# Default resource types
DEFAULT_RESOURCE_TYPES = ['Humano', 'Local', 'Máquina', 'Próprio']