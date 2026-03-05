# seed.py
from faker import Faker
import random
from database import SessionLocal, engine
import models
from main import hash_password  # Import your password hasher

# ---------------- CREATE TABLES ----------------
models.Base.metadata.create_all(bind=engine)

fake = Faker()
db = SessionLocal()

# ---- CLEAR OLD DATA ----
db.query(models.Project).delete()
db.query(models.Contractor).delete()
db.query(models.Directorate).delete()
db.query(models.User).delete()
db.commit()
print("Old data cleared...")

# ---- CREATE DIRECTORATES ----
directorate_names = [
    "Planning & Design",
    "Road Maintenance",
    "Construction Management",
    "Bridge Engineering",
    "Materials & Testing",
    "Quality Assurance",
    "Finance & Administration",
    "ICT & Innovation",
    "Environmental & Social Safeguards",
    "Procurement & Supply Chain"
]

directorates = []
for name in directorate_names:
    d = models.Directorate(name=name)
    db.add(d)
    directorates.append(d)

db.commit()
# Refresh to populate IDs
for d in directorates:
    db.refresh(d)

print("Directorates created...")

# ---- CREATE CONTRACTORS ----
contractors = []
for _ in range(40):
    c = models.Contractor(name=fake.company(), contact=fake.phone_number())
    db.add(c)
    contractors.append(c)

db.commit()
for c in contractors:
    db.refresh(c)

print("Contractors created...")

# ---- CREATE PROJECTS ----
statuses = ["Active", "Completed", "Delayed"]
project_names = [
    "Nairobi - Mombasa Highway Expansion",
    "Thika Superhighway Rehabilitation",
    "Kisumu Bypass Construction",
    "Eldoret Eastern Bypass Upgrade",
    "Nakuru - Mau Summit Road Improvement",
    "Machakos Turnoff Interchange Development",
    "Garissa Highway Upgrade",
    "Malindi Coastal Road Expansion"
]

for _ in range(300):
    budget = random.randint(50_000_000, 2_000_000_000)
    spent = random.randint(10_000_000, budget)  # ensure spent <= budget
    progress = (spent / budget) * 100 if budget > 0 else 0

    project = models.Project(
        name=random.choice(project_names) + f" Phase {random.randint(1,5)}",
        budget=budget,
        spent=spent,
        progress=progress,
        status=random.choice(statuses),
        directorate_id=random.choice(directorates).id,
        contractor_id=random.choice(contractors).id
    )
    db.add(project)

db.commit()
print("Projects created...")

# ---- CREATE ENGINEERS ----
for d in directorates:
    for _ in range(2):  # 2 engineers per directorate
        user = models.User(
            username=fake.user_name(),
            password=hash_password("password123"),  # hashed password
            role="Engineer",
            directorate_id=d.id
        )
        db.add(user)
db.commit()
print("Engineers created...")

# ---- CREATE DEFAULT ADMIN ----
if not db.query(models.User).filter(models.User.username == "admin").first():
    admin = models.User(
        username="admin",
        password=hash_password("admin123"),
        role="Admin"
    )
    db.add(admin)
    db.commit()
    print("Admin created...")

db.close()
print("DATABASE SEEDED SUCCESSFULLY 🚀")