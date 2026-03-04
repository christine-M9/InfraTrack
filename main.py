from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import models, schemas
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# -------- DATABASE DEPENDENCY --------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------- FRONTEND ROUTES --------

@app.get("/")
def dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/projects-page")
def projects_page():
    return FileResponse("static/projects.html")

@app.get("/project-detail")
def project_detail():
    return FileResponse("static/project-detail.html")

@app.get("/directorates-page")
def directorates_page():
    return FileResponse("static/directorates.html")

@app.get("/contractors-page")
def contractors_page():
    return FileResponse("static/contractors.html")

@app.get("/reports-page")
def reports_page():
    return FileResponse("static/reports.html")

# -------- DIRECTORATES API --------

@app.get("/directorates", response_model=list[schemas.DirectorateOut])
def get_directorates(db: Session = Depends(get_db)):
    directorates = db.query(models.Directorate).all()

    result = []

    for d in directorates:
        projects = d.projects

        project_count = len(projects)
        total_budget = sum(p.budget for p in projects)

        total_spent = sum(p.spent for p in projects)

        completion_percent = 0
        if total_budget > 0:
            completion_percent = (total_spent / total_budget) * 100

        # Flag delayed if any project over budget
        has_delayed = any(p.spent > p.budget for p in projects)

        result.append({
            "id": d.id,
            "name": d.name,
            "project_count": project_count,
            "total_budget": total_budget,
            "completion_percent": completion_percent,
            "has_delayed": has_delayed
        })

    return result
@app.post("/directorates", response_model=schemas.DirectorateOut)
def create_directorate(d: schemas.DirectorateCreate, db: Session = Depends(get_db)):
    directorate = models.Directorate(name=d.name)
    db.add(directorate)
    db.commit()
    db.refresh(directorate)
    return directorate

@app.delete("/directorates/{id}")
def delete_directorate(id: int, db: Session = Depends(get_db)):
    d = db.query(models.Directorate).get(id)
    if not d:
        raise HTTPException(status_code=404)
    db.delete(d)
    db.commit()
    return {"message": "Deleted"}

# -------- CONTRACTORS API --------

@app.get("/contractors", response_model=list[schemas.ContractorOut])
def get_contractors(db: Session = Depends(get_db)):
    contractors = db.query(models.Contractor).all()

    result = []
    for c in contractors:
        result.append({
            "id": c.id,
            "name": c.name,
            "contact": c.contact,
            "project_count": len(c.projects)
        })

    return result
@app.post("/contractors", response_model=schemas.ContractorOut)
def create_contractor(c: schemas.ContractorCreate, db: Session = Depends(get_db)):
    contractor = models.Contractor(name=c.name, contact=c.contact)
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return contractor

@app.delete("/contractors/{id}")
def delete_contractor(id: int, db: Session = Depends(get_db)):
    c = db.query(models.Contractor).get(id)
    if not c:
        raise HTTPException(status_code=404)
    db.delete(c)
    db.commit()
    return {"message": "Deleted"}

# -------- PROJECTS API --------

@app.get("/projects", response_model=list[schemas.ProjectOut])
def get_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@app.post("/projects", response_model=schemas.ProjectOut)
def create_project(p: schemas.ProjectCreate, db: Session = Depends(get_db)):
    progress = 0
    if p.budget > 0:
        progress = (p.spent / p.budget) * 100

    project = models.Project(
        name=p.name,
        budget=p.budget,
        spent=p.spent,
        progress=progress,
        directorate_id=p.directorate_id,
        contractor_id=p.contractor_id
    )

    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@app.delete("/projects/{id}")
def delete_project(id: int, db: Session = Depends(get_db)):
    p = db.query(models.Project).get(id)
    if not p:
        raise HTTPException(status_code=404)
    db.delete(p)
    db.commit()
    return {"message": "Deleted"}

@app.get("/directorate-projects-page")
def directorate_projects_page():
    return FileResponse("static/directorate-projects.html")    