from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import date
from jose import jwt

from auth import hash_password, verify_password, create_token
import models, schemas
from database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="InfraTrack Enterprise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= AUTH =================
SECRET_KEY = "secretkey123"
ALGORITHM = "HS256"

security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

# ================= BUSINESS LOGIC =================

def get_status(project):
    if project.progress >= 100:
        return "Completed"
    if project.spent > project.budget:
        return "Over Budget"
    if date.today() > project.deadline:
        return "Delayed"
    return "On Track"

def risk_level(project):
    if project.spent > project.budget:
        return "Financial Risk"
    if project.progress < 50 and date.today() > project.deadline:
        return "High Risk"
    return "Low Risk"

# ================= PROJECT ROUTES =================

@app.post("/projects", response_model=schemas.ProjectOut)
def create_project(
    project: schemas.ProjectCreate,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_project = models.Project(
        name=project.name,
        contractor=project.contractor,
        location=project.location,
        deadline=project.deadline,
        progress=0,
        budget=project.budget,
        spent=project.spent
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return {
        **db_project.__dict__,
        "status": get_status(db_project),
        "risk": risk_level(db_project),
        "remaining": db_project.budget - db_project.spent
    }


@app.get("/projects", response_model=list[schemas.ProjectOut])
def get_projects(
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(models.Project).all()

    result = []
    for p in projects:
        result.append({
            **p.__dict__,
            "status": get_status(p),
            "risk": risk_level(p),
            "remaining": p.budget - p.spent
        })

    return result

@app.put("/projects/{project_id}")
def update_project(project_id: int, updated: schemas.ProjectUpdate, db: Session = Depends(get_db)):

    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    return project

@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"message": "Project deleted"}


# ================= AUTH ROUTES =================

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()

    if existing:
        raise HTTPException(400, "Username exists")

    new = models.User(
        username=user.username,
        password=hash_password(user.password)
    )

    db.add(new)
    db.commit()

    return {"message": "User created"}


@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(401, "Invalid credentials")

    token = create_token({"sub": db_user.username})

    return {"access_token": token}