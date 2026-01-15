from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import date
from typing import Optional
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi import Query
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# ---------------------------------------------------------
# 1. DATABASE CONFIGURATION
# ---------------------------------------------------------
DATABASE_URL = "postgresql://postgres:061204@localhost:5432/rwe_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 2. DATABASE MODELS
# ---------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    diagnosis = Column(String)
    bcva = Column(Float)
    irf = Column(Boolean)
    srf = Column(Boolean)

class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    visit_date = Column(Date)
    bcva = Column(Float)
    injections = Column(Integer, default=0)
    irf = Column(Boolean, default=False)
    srf = Column(Boolean, default=False)
    hard_exudates = Column(Boolean, default=False)
    hrf = Column(Boolean, default=False)
    molecule = Column(String, default="")
    regimen = Column(String, default="")

class AdverseEvent(Base):
    __tablename__ = "adverse_events"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    visit_id = Column(Integer, ForeignKey("visits.id"))
    description = Column(String)
    severity = Column(String)
    date_reported = Column(Date)

# Create all tables in PostgreSQL
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------
# 3. FASTAPI APP SETUP
# ---------------------------------------------------------
app = FastAPI(title="RWE Ophthalmology Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "RWE Backend Running"}

# ✅ THIS IS THE MISSING API
@app.get("/patients")
def get_patients():
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        return patients
    finally:
        db.close()

@app.get("/patients/filter")
def filter_patients(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
):
    db = SessionLocal()
    query = db.query(Patient)

    if diagnosis:
        query = query.filter(Patient.diagnosis == diagnosis)

    if min_age is not None:
        query = query.filter(Patient.age >= min_age)

    if max_age is not None:
        query = query.filter(Patient.age <= max_age)

    results = query.all()
    db.close()
    return results
# ---------------------------------------------------------
# 4. DATA ENTRY APIs (POST)
# ---------------------------------------------------------
@app.post("/patients")
def add_patient(
    age: int,
    gender: str,
    diagnosis: str,
    bcva: float,
    irf: bool,
    srf: bool,
    db: Session = Depends(get_db)
):
    patient = Patient(
        age=age,
        gender=gender,
        diagnosis=diagnosis,
        bcva=bcva,
        irf=irf,
        srf=srf
    )
    db.add(patient)
    db.commit()
    return {"message": "Patient added"}

@app.post("/visits")
def add_visit(patient_id: int, visit_date: date, bcva: float, injections: int,
              irf: bool, srf: bool, hard_exudates: bool, hrf: bool,
              molecule: str, regimen: str, db: Session = Depends(get_db)):
    visit = Visit(patient_id=patient_id, visit_date=visit_date, bcva=bcva, 
                  injections=injections, irf=irf, srf=srf, 
                  hard_exudates=hard_exudates, hrf=hrf,
                  molecule=molecule, regimen=regimen)
    db.add(visit)
    db.commit()
    return {"message": "Visit added"}

# ---------------------------------------------------------
# 5. ANALYTICS APIs (GET)
# ---------------------------------------------------------

@app.get("/analytics/bcva-filtered")
def filtered_bcva(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """BCVA over time with optional clinical filters.

    This endpoint is the *single source of truth* for filter logic so that
    frontend charts and the PDF export stay consistent.
    """

    query = (
        "SELECT v.visit_date, v.bcva "
        "FROM visits v JOIN patients p ON v.patient_id = p.id "
        "WHERE 1=1"
    )
    params = {}

    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis

    if min_age is not None:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age

    if max_age is not None:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age

    if start_date is not None:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date is not None:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    query += " ORDER BY v.visit_date"
    result = db.execute(text(query), params)
    return [{"date": r[0], "bcva": r[1]} for r in result]

@app.get("/analytics/injection-bcva")
def injection_vs_bcva(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Average BCVA by injection count, with the same filters as /analytics/bcva-filtered."""

    query = (
        "SELECT v.injections, AVG(v.bcva) "
        "FROM visits v JOIN patients p ON v.patient_id = p.id "
        "WHERE 1=1"
    )
    params = {}

    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis

    if min_age is not None:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age

    if max_age is not None:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age

    if start_date is not None:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date is not None:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    query += " GROUP BY v.injections ORDER BY v.injections"
    result = db.execute(text(query), params)
    return [{"injections": r[0], "avg_bcva": r[1]} for r in result]


@app.get("/analytics/fluid")
def fluid_analysis(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """IRF / SRF counts with optional filters."""

    query = (
        "SELECT "
        "SUM(CASE WHEN v.irf=true THEN 1 ELSE 0 END) AS irf_count, "
        "SUM(CASE WHEN v.srf=true THEN 1 ELSE 0 END) AS srf_count "
        "FROM visits v JOIN patients p ON v.patient_id = p.id "
        "WHERE 1=1"
    )
    params = {}

    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis

    if min_age is not None:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age

    if max_age is not None:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age

    if start_date is not None:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date is not None:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    result = db.execute(text(query), params).fetchone()
    return [
        {"type": "IRF", "count": (result[0] or 0) if result else 0},
        {"type": "SRF", "count": (result[1] or 0) if result else 0},
    ]


@app.get("/analytics/hard-hrf")
def hard_hrf_analysis(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Hard exudates / HRF counts with optional filters."""

    query = (
        "SELECT "
        "SUM(CASE WHEN v.hard_exudates=true THEN 1 ELSE 0 END) AS hard_exudates_count, "
        "SUM(CASE WHEN v.hrf=true THEN 1 ELSE 0 END) AS hrf_count "
        "FROM visits v JOIN patients p ON v.patient_id = p.id "
        "WHERE 1=1"
    )
    params = {}

    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis

    if min_age is not None:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age

    if max_age is not None:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age

    if start_date is not None:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date is not None:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    result = db.execute(text(query), params).fetchone()
    return [
        {"type": "Hard Exudates", "count": (result[0] or 0) if result else 0},
        {"type": "HRF", "count": (result[1] or 0) if result else 0},
    ]


# ---------------------------------------------------------
# 6. PDF EXPORT API
# ---------------------------------------------------------
@app.get("/export/pdf")
def export_pdf(
    diagnosis: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Generate a PDF report using the *same filters* as /analytics/bcva-filtered.

    Whatever is visible on the dashboard for BCVA should match this export.
    """

    query = (
        "SELECT v.visit_date, v.bcva, v.injections, p.age, p.diagnosis "
        "FROM visits v JOIN patients p ON v.patient_id = p.id "
        "WHERE 1=1"
    )
    params = {}

    if diagnosis:
        query += " AND p.diagnosis = :diagnosis"
        params["diagnosis"] = diagnosis

    if min_age is not None:
        query += " AND p.age >= :min_age"
        params["min_age"] = min_age

    if max_age is not None:
        query += " AND p.age <= :max_age"
        params["max_age"] = max_age

    if start_date is not None:
        query += " AND v.visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date is not None:
        query += " AND v.visit_date <= :end_date"
        params["end_date"] = end_date

    result = db.execute(text(query), params).fetchall()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle("RWE Ophthalmology Report")

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "Ophthalmology RWE Platform Report")
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, f"Report Generated: {date.today()}")

    # Table Header
    y = 700
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Date")
    p.drawString(130, y, "BCVA")
    p.drawString(180, y, "Injections")
    p.drawString(250, y, "Age")
    p.drawString(300, y, "Diagnosis")
    p.line(50, y-5, 550, y-5)

    # Data Rows
    y -= 20
    p.setFont("Helvetica", 10)
    for row in result:
        if y < 50:  # New page if bottom reached
            p.showPage()
            y = 750
        p.drawString(50, y, str(row[0]))
        p.drawString(130, y, str(row[1]))
        p.drawString(180, y, str(row[2]))
        p.drawString(250, y, str(row[3]))
        p.drawString(300, y, str(row[4]))
        y -= 20

    p.save()
    buffer.seek(0)
    return StreamingResponse(
    buffer,
    media_type="application/pdf",
    headers={"Content-Disposition": "attachment; filename=Ophthalmology_Report.pdf"}
)
