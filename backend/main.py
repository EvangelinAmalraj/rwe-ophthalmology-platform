from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date
from typing import Optional
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# ---------------- DATABASE ----------------
DATABASE_URL = "postgresql://postgres:061204@localhost:5432/rwe_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    gender = Column(String)
    diagnosis = Column(String)
    co_morbidities = Column(String)
    medications = Column(String)

class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer)
    visit_date = Column(Date)
    bcva = Column(Float)
    injections = Column(Integer)
    irf = Column(Boolean)
    srf = Column(Boolean)
    hard_exudates = Column(Boolean)
    hrf = Column(Boolean)
    molecule = Column(String)
    regimen = Column(String)

class AdverseEvent(Base):
    __tablename__ = "adverse_events"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer)
    visit_id = Column(Integer)
    description = Column(String)
    severity = Column(String)
    date_reported = Column(Date)

Base.metadata.create_all(engine)

# ---------------- PATIENT APIs ----------------
@app.post("/patients")
def add_patient(age: int, gender: str, diagnosis: str,
                co_morbidities: str = "", medications: str = ""):
    db = SessionLocal()
    patient = Patient(age=age, gender=gender, diagnosis=diagnosis,
                      co_morbidities=co_morbidities, medications=medications)
    db.add(patient)
    db.commit()
    return {"message": "Patient added"}

@app.post("/visits")
def add_visit(patient_id: int, visit_date: date, bcva: float, injections: int,
              irf: bool, srf: bool, hard_exudates: bool, hrf: bool,
              molecule: str, regimen: str):
    db = SessionLocal()
    visit = Visit(patient_id=patient_id, visit_date=visit_date,
                  bcva=bcva, injections=injections, irf=irf, srf=srf,
                  hard_exudates=hard_exudates, hrf=hrf,
                  molecule=molecule, regimen=regimen)
    db.add(visit)
    db.commit()
    return {"message": "Visit added"}

@app.post("/adverse-events")
def add_adverse_event(patient_id: int, visit_id: int, description: str,
                      severity: str, date_reported: date):
    db = SessionLocal()
    event = AdverseEvent(patient_id=patient_id, visit_id=visit_id,
                         description=description, severity=severity,
                         date_reported=date_reported)
    db.add(event)
    db.commit()
    return {"message": "Adverse event added"}

# ---------------- ANALYTICS ----------------
@app.get("/analytics/bcva-filtered")
def filtered_bcva(diagnosis: Optional[str] = None,
                  min_age: Optional[int] = None,
                  max_age: Optional[int] = None,
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None):

    # Convert empty strings to None
    if diagnosis == "":
        diagnosis = None
    if min_age == "" or min_age is None:
        min_age = None
    if max_age == "" or max_age is None:
        max_age = None
    if start_date == "":
        start_date = None
    if end_date == "":
        end_date = None

    query = "SELECT v.visit_date, v.bcva FROM visits v JOIN patients p ON v.patient_id = p.id WHERE 1=1"
    params = {}
    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis
    if min_age:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age
    if max_age:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age
    if start_date:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date
    query += " ORDER BY v.visit_date"

    result = engine.execute(text(query), params)
    return [{"date": r[0], "bcva": r[1]} for r in result]

@app.get("/analytics/injection-bcva")
def injection_vs_bcva():
    result = engine.execute(text("SELECT injections, AVG(bcva) FROM visits GROUP BY injections ORDER BY injections"))
    return [{"injections": r[0], "avg_bcva": r[1]} for r in result]

@app.get("/analytics/fluid")
def fluid_analysis():
    result = engine.execute(text("SELECT SUM(CASE WHEN irf=true THEN 1 ELSE 0 END), SUM(CASE WHEN srf=true THEN 1 ELSE 0 END) FROM visits")).fetchone()
    return [{"type": "IRF", "count": result[0]}, {"type": "SRF", "count": result[1]}]

@app.get("/analytics/hard-hrf")
def hard_hrf_analysis():
    result = engine.execute(text("SELECT SUM(CASE WHEN hard_exudates=true THEN 1 ELSE 0 END), SUM(CASE WHEN hrf=true THEN 1 ELSE 0 END) FROM visits")).fetchone()
    return [{"type": "Hard Exudates", "count": result[0]}, {"type": "HRF", "count": result[1]}]

# ---------------- PDF EXPORT ----------------
@app.get("/export/pdf")
def export_pdf(diagnosis: Optional[str] = None,
               min_age: Optional[int] = None,
               max_age: Optional[int] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None):

    # Convert empty strings to None
    if diagnosis == "":
        diagnosis = None
    if min_age == "" or min_age is None:
        min_age = None
    if max_age == "" or max_age is None:
        max_age = None
    if start_date == "":
        start_date = None
    if end_date == "":
        end_date = None

    query = "SELECT v.visit_date, v.bcva, v.injections, p.age, p.diagnosis FROM visits v JOIN patients p ON v.patient_id = p.id WHERE 1=1"
    params = {}
    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis
    if min_age:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age
    if max_age:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age
    if start_date:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    result = engine.execute(text(query), params).fetchall()

    # Create PDF
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("RWE Ophthalmology Report")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 750, "Ophthalmology RWE Report")

    pdf.setFont("Helvetica", 12)
    y = 720
    pdf.drawString(50, y, "Filters Applied:")
    pdf.drawString(150, y, f"Diagnosis: {diagnosis or 'All'}, Age: {min_age or 'NA'}-{max_age or 'NA'}, Date: {start_date or 'NA'}-{end_date or 'NA'}")

    y -= 30
    pdf.drawString(50, y, "Date       BCVA     Injections     Age     Diagnosis")
    y -= 20

    for row in result:
        date_str = row[0].strftime("%Y-%m-%d")
        bcva = row[1]
        inj = row[2]
        age = row[3]
        diag = row[4]
        pdf.drawString(50, y, f"{date_str}   {bcva}          {inj}            {age}      {diag}")
        y -= 20
        if y < 50:
            pdf.showPage()
            y = 750

    pdf.save()
    buffer.seek(0)

    return FileResponse(buffer, media_type="application/pdf", filename="RWE_Report.pdf")

