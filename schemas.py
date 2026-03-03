from pydantic import BaseModel
from datetime import date
from typing import Optional

# ---------- PROJECT ----------

class ProjectCreate(BaseModel):
    name: str
    contractor: str
    location: str
    deadline: date
    budget: float
    spent: float


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    contractor: Optional[str] = None
    location: Optional[str] = None
    deadline: Optional[date] = None
    budget: Optional[float] = None
    spent: Optional[float] = None
    progress: Optional[float] = None

class ProjectOut(BaseModel):
    id: int
    name: str
    contractor: str
    location: str
    deadline: date
    progress: float
    budget: float
    spent: float
    remaining: float
    status: str
    risk: str

    class Config:
        orm_mode = True


# ---------- USER ----------

class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str