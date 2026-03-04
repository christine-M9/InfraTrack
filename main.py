from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import models, schemas
from database import engine, SessionLocal
from openpyxl import Workbook
from sklearn.linear_model import LinearRegression
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import numpy as np
import io

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
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
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

# ---------------- LOGIN ----------------
@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": user.username, "role": user.role, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"access_token": token}

# ---------------- FRONTEND ROUTES ----------------
@app.get("/")
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

# ---------------- CONTRACTORS JSON ----------------
@app.get("/contractors")
def get_contractors(db: Session = Depends(get_db)):
    """
    Returns all contractors with:
    - id
    - name
    - contact
    - total projects
    """
    contractors = db.query(models.Contractor).all()
    result = []
    for c in contractors:
        result.append({
            "id": c.id,
            "name": c.name,
            "contact": c.contact if hasattr(c, "contact") else "N/A",  # optional contact field
            "project_count": len(c.projects)  # total projects linked to this contractor
        })
    return result
# ---------------- PROJECTS ----------------
@app.get("/projects")
def get_projects(db: Session = Depends(get_db)):
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
def create_project(p: schemas.ProjectCreate, db: Session = Depends(get_db)):
    progress = (p.spent / p.budget)*100 if p.budget>0 else 0
    project = models.Project(
        name=p.name,
        budget=p.budget,
        spent=p.spent,
        progress=progress,
        status=p.status,
        directorate_id=p.directorate_id,
        contractor_id=p.contractor_id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@app.delete("/projects/{id}")
def delete_project(id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = db.query(models.Project).get(id)
    if not p: raise HTTPException(status_code=404)
    db.delete(p)
    db.commit()
    log_action(db, user["sub"], f"Deleted project {id}")
    return {"message": "Deleted"}

# ---------------- DIRECTORATES ----------------
@app.get("/directorates")
def get_directorates(db: Session = Depends(get_db)):
    directorates = db.query(models.Directorate).all()
    result = []
    for d in directorates:
        projects = d.projects
        total_budget = sum(p.budget for p in projects)
        total_spent = sum(p.spent for p in projects)
        completion_percent = (total_spent/total_budget*100) if total_budget>0 else 0
        has_delayed = any(p.status=="Delayed" for p in projects)
        result.append({
            "id": d.id,
            "name": d.name,
            "project_count": len(projects),
            "total_budget": total_budget,
            "completion_percent": completion_percent,
            "has_delayed": has_delayed
        })
    return result

# ---------------- EXPORT EXCEL ----------------
@app.get("/directorates/{id}/export")
def export_directorate_excel(id:int, db: Session = Depends(get_db)):
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

# ---------------- ANALYTICS ----------------
@app.get("/directorates/{id}/analytics")
def directorate_analytics(id:int, db: Session=Depends(get_db)):
    projects = db.query(models.Project).filter(models.Project.directorate_id==id).all()
    total_budget = sum(p.budget for p in projects)
    total_spent = sum(p.spent for p in projects)
    status_counts = {"Active":0,"Completed":0,"Delayed":0}
    for p in projects: status_counts[p.status]+=1
    return {"total_budget": total_budget,"total_spent":total_spent,"status_distribution":status_counts}

# ---------------- CONTRACTOR RANKING ----------------
@app.get("/contractor-ranking")
def contractor_ranking(db: Session = Depends(get_db)):
    contractors = db.query(models.Contractor).all()
    ranking = []
    for c in contractors:
        projects = c.projects
        if not projects: continue
        avg_variance = sum((p.spent-p.budget)/p.budget if p.budget>0 else 0 for p in projects)/len(projects)
        ranking.append({"contractor": c.name, "projects": len(projects), "avg_variance_percent": round(avg_variance*100,2)})
    ranking.sort(key=lambda x: x["avg_variance_percent"])
    return ranking

# ---------------- AI PREDICT ----------------
@app.get("/predict-overrun/{project_id}")
def predict_overrun(project_id:int, db:Session=Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project: raise HTTPException(status_code=404)
    X = np.array([[project.progress]])
    y = np.array([project.spent])
    model = LinearRegression()
    model.fit(X, y)
    predicted_spent = model.predict([[100]])[0]
    overrun = predicted_spent - project.budget
    return {"predicted_final_spent":float(predicted_spent),"predicted_overrun":float(overrun)}

@app.get("/contractor-projects-page")
def contractor_projects_page():
    return FileResponse("static/contractor-projects.html")    