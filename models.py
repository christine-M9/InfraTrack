from sqlalchemy import Column, Integer, String, Float, Date
from database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contractor = Column(String, nullable=False)
    location = Column(String, nullable=False)
    deadline = Column(Date, nullable=False)
    progress = Column(Float, default=0)

    # ✅ NEW FINANCIAL FIELDS
    budget = Column(Float, default=0)
    spent = Column(Float, default=0)


class User(Base):
    __tablename__="users"

    id=Column(Integer, primary_key=True, index=True)
    username=Column(String, unique=True)
    password=Column(String)