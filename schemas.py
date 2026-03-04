from pydantic import BaseModel

# ----------------- Auth -----------------
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str

# ----------------- Project / Contractor / Directorate -----------------
from typing import Optional

class DirectorateBase(BaseModel):
    name: str

class DirectorateCreate(DirectorateBase):
    pass

class DirectorateOut(BaseModel):
    id: int
    name: str
    project_count: int
    total_budget: float
    completion_percent: float
    has_delayed: bool
    class Config:
        orm_mode = True

class ContractorBase(BaseModel):
    name: str
    contact: Optional[str] = None

class ContractorCreate(ContractorBase):
    pass

class ContractorOut(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    project_count: int
    class Config:
        orm_mode = True

class ProjectBase(BaseModel):
    name: str
    budget: float
    spent: float
    directorate_id: int
    contractor_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    progress: float
    status: str
    class Config:
        orm_mode = True