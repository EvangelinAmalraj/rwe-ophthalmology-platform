import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# Database connection
engine = create_engine("postgresql://postgres:061204@localhost:5432/rwe_db")

# Read data
df = pd.read_sql("patients", engine)

# Check if data exists
if df.empty:
    print("No data found. Please add patient records first.")
    exit()

# ---- TEXT INSIGHTS ----
print("Average age:", df["age"].mean())
print("\nDiagnosis count:")
print(df["diagnosis"].value_counts())

# ---- VISUAL 1: Diagnosis Count Bar Chart ----
plt.figure()
df["diagnosis"].value_counts().plot(kind="bar")
plt.title("Patient Count by Diagnosis")
plt.xlabel("Diagnosis")
plt.ylabel("Number of Patients")
plt.tight_layout()
plt.show()
