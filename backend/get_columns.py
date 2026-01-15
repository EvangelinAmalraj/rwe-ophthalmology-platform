from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:061204@localhost:5432/rwe_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    result = connection.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'visits'"))
    columns = [row[0] for row in result]
    print(columns)