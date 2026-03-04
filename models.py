from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Directorate(Base):
    __tablename__ = "directorates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    projects = relationship("Project", back_populates="directorate")


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact = Column(String)

    projects = relationship("Project", back_populates="contractor")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    budget = Column(Float, default=0)
    spent = Column(Float, default=0)
    progress = Column(Float, default=0)
    status = Column(String, default="Active")

    directorate_id = Column(Integer, ForeignKey("directorates.id"))
    contractor_id = Column(Integer, ForeignKey("contractors.id"))

    directorate = relationship("Directorate", back_populates="projects")
    contractor = relationship("Contractor", back_populates="projects")