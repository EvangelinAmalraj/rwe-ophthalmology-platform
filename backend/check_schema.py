from sqlalchemy import create_engine, inspect
import json

DATABASE_URL = "postgresql://postgres:061204@localhost:5432/rwe_db"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

columns = inspector.get_columns("visits")
print(json.dumps([c["name"] for c in columns]))