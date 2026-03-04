from faker import Faker
import random
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

fake = Faker()
db = SessionLocal()

# ---- CLEAR OLD DATA ----
db.query(models.Project).delete()
db.query(models.Contractor).delete()
db.query(models.Directorate).delete()
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

print("Directorates created...")

# ---- CREATE CONTRACTORS ----
contractors = []

for _ in range(40):
    c = models.Contractor(
        name=fake.company(),
        contact=fake.phone_number()
    )
    db.add(c)
    contractors.append(c)

db.commit()

print("Contractors created...")

# ---- CREATE PROJECTS ----
statuses = ["Active", "Completed", "Delayed"]

for _ in range(300):

    budget = random.randint(50_000_000, 2_000_000_000)
    spent = random.randint(10_000_000, budget + 500_000_000)

    progress = 0
    if budget > 0:
        progress = (spent / budget) * 100

    project_name = random.choice([
        "Nairobi - Mombasa Highway Expansion",
        "Thika Superhighway Rehabilitation",
        "Kisumu Bypass Construction",
        "Eldoret Eastern Bypass Upgrade",
        "Nakuru - Mau Summit Road Improvement",
        "Machakos Turnoff Interchange Development",
        "Garissa Highway Upgrade",
        "Malindi Coastal Road Expansion"
    ]) + f" Phase {random.randint(1,5)}"

    project = models.Project(
        name=project_name,
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
print("DATABASE SEEDED SUCCESSFULLY 🚀")

db.close()