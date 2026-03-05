from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import models, schemas
from database import engine, SessionLocal
from openpyxl import Workbook
import io
from sqlalchemy.orm import joinedload


# ---------------- CREATE TABLES ----------------
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------- AUTH CONFIG ----------------
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ---------------- DATABASE ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- PASSWORD HELPERS ----------------
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

# ---------------- AUTH HELPERS ----------------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------- AUDIT LOGGER ----------------
def log_action(db, username, action):
    log = models.AuditLog(
        user=username,
        action=action,
        timestamp=str(datetime.utcnow())
    )
    db.add(log)
    db.commit()

# ---------------- AUTO CREATE ADMIN ----------------
@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        new_admin = models.User(
            username="admin",
            password=hash_password("admin123"),
            role="Admin"
        )
        db.add(new_admin)
        db.commit()
    db.close()

# ---------------- SCHEMAS FOR LOGIN/REGISTER ----------------
from pydantic import BaseModel
from typing import Optional

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    role: Optional[str] = "Engineer"      # Admin, DirectorGeneral, Engineer
    directorate_id: Optional[int] = None  # Only for Engineers

# ---------------- LOGIN ----------------
@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": user.username,
            "role": user.role,
            "directorate_id": getattr(user, "directorate_id", None),
            "exp": expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    log_action(db, data.username, "Logged in")
    return {
        "access_token": token,
        "role": user.role,
        "directorate_id": getattr(user, "directorate_id", None)
    }

# ---------------- REGISTER ----------------
@app.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = models.User(
        username=data.username,
        password=hash_password(data.password),
        role=data.role or "Engineer",
        directorate_id=data.directorate_id
    )
    db.add(new_user)
    db.commit()
    log_action(db, data.username, "Registered new account")
    return {"message": "User registered successfully"}

# ---------------- FRONTEND ROUTES ----------------
@app.get("/")
def home():
    return FileResponse("static/home.html")

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/projects-page")
def projects_page():
    return FileResponse("static/projects.html")

@app.get("/directorates-page")
def directorates_page():
    return FileResponse("static/directorates.html")

@app.get("/contractors-page")
def contractors_page():
    return FileResponse("static/contractors.html")

@app.get("/reports-page")
def reports_page():
    return FileResponse("static/reports.html")

@app.get("/directorate-projects-page")
def directorate_projects_page():
    return FileResponse("static/directorate-projects.html")

@app.get("/contractor-projects-page")
def contractor_projects_page():
    return FileResponse("static/contractor-projects.html")

@app.get("/audit-logs-page")
def audit_logs_page():
    return FileResponse("static/audit-logs.html")
# ---------------- CONTRACTORS ----------------
@app.get("/contractors")
def get_contractors(db: Session = Depends(get_db)):
    contractors = db.query(models.Contractor).all()
    result = []
    for c in contractors:
        result.append({
            "id": c.id,
            "name": c.name,
            "contact": getattr(c, "contact", "N/A"),
            "project_count": len(c.projects)
        })
    return result

# ---------------- PROJECTS ----------------
@app.get("/projects")
def get_projects(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] == "Engineer":
        projects = db.query(models.Project).filter(
            models.Project.directorate_id == user.get("directorate_id")
        ).all()
    else:
        projects = db.query(models.Project).all()
    result = []
    for p in projects:
        variance_percent = ((p.spent - p.budget)/p.budget*100) if p.budget>0 else 0
        risk_score = 0
        if variance_percent > 20: risk_score += 40
        if p.progress < 50 and variance_percent > 10: risk_score += 30
        if p.status == "Delayed": risk_score += 30
        result.append({
            "id": p.id,
            "name": p.name,
            "budget": p.budget,
            "spent": p.spent,
            "progress": p.progress,
            "status": p.status,
            "variance_percent": round(variance_percent,2),
            "risk_score": risk_score,
            "directorate": p.directorate.name if p.directorate else None,
            "directorate_id": p.directorate_id,
            "contractor": p.contractor.name if p.contractor else None,
            "contractor_id": p.contractor_id
        })
    return result

@app.post("/projects")
def create_project(p: schemas.ProjectCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ["Admin","DirectorGeneral"]:
        raise HTTPException(status_code=403, detail="Not authorized to create project")
    if not db.query(models.Directorate).get(p.directorate_id):
        raise HTTPException(status_code=400, detail="Invalid directorate ID")
    if p.contractor_id and not db.query(models.Contractor).get(p.contractor_id):
        raise HTTPException(status_code=400, detail="Invalid contractor ID")
    progress = (p.spent / p.budget)*100 if p.budget > 0 else 0
    project = models.Project(
        name=p.name,
        budget=p.budget,
        spent=p.spent,
        progress=progress,
        status=getattr(p, "status", "Active"),
        directorate_id=p.directorate_id,
        contractor_id=p.contractor_id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    log_action(db, user["sub"], f"Created project {project.name} (ID {project.id})")
    return project

@app.delete("/projects/{id}")
def delete_project(id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    project = db.query(models.Project).get(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    log_action(db, user["sub"], f"Deleted project {project.name} (ID {project.id})")
    return {"message": "Deleted"}

# ---------------- DIRECTORATES ----------------
@app.get("/directorates")
def get_directorates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Load directorates with projects eagerly
    query = db.query(models.Directorate).options(joinedload(models.Directorate.projects))
    
    # Filter for Engineers
    if user["role"] == "Engineer":
        query = query.filter(models.Directorate.id == user.get("directorate_id"))
    
    directorates = query.all()
    
    result = []
    for d in directorates:
        projects = d.projects  # Already loaded thanks to joinedload
        total_budget = sum(p.budget for p in projects)
        total_spent = sum(p.spent for p in projects)
        completion_percent = (total_spent / total_budget * 100) if total_budget > 0 else 0
        has_delayed = any(p.status == "Delayed" for p in projects)
        result.append({
            "id": d.id,
            "name": d.name,
            "project_count": len(projects),
            "total_budget": total_budget,
            "completion_percent": round(completion_percent,2),
            "has_delayed": has_delayed
        })
    return result

# ---------------- EXPORT EXCEL ----------------
@app.get("/directorates/{id}/export")
def export_directorate_excel(id:int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] == "Engineer" and id != user.get("directorate_id"):
        raise HTTPException(status_code=403, detail="Not authorized to export this directorate")
    projects = db.query(models.Project).filter(models.Project.directorate_id==id).all()
    wb = Workbook()
    ws = wb.active
    ws.append(["Project","Contractor","Budget","Spent","Progress","Status"])
    for p in projects:
        ws.append([
            p.name,
            p.contractor.name if p.contractor else "N/A",
            p.budget,
            p.spent,
            p.progress,
            p.status
        ])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=directorate_projects.xlsx"}
    )

# ---------------- AUDIT LOGS ----------------
@app.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).all()
    return [
        {"id": log.id, "user": log.user, "action": log.action, "timestamp": log.timestamp}
        for log in logs
    ]