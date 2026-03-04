# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# ---------------- DIRECTORATE ----------------
class Directorate(Base):
    __tablename__ = "directorates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    projects = relationship("Project", back_populates="directorate")


# ---------------- CONTRACTOR ----------------
class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact = Column(String)  # <-- important to show on frontend

    projects = relationship("Project", back_populates="contractor")


# ---------------- PROJECT ----------------
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


# ---------------- USER ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Admin, Engineer, Auditor


# ---------------- AUDIT LOG ----------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    user = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)