from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# --------------------------
# DATABASE FILE LOCATION
# --------------------------
DB_FILE = "voiceai.db"
DB_URL = f"sqlite:///{DB_FILE}"

# --------------------------
# SQLAlchemy engine
# --------------------------
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False}
)

# --------------------------
# Session Local
# --------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# --------------------------
# Base Model
# --------------------------
Base = declarative_base()

# --------------------------
# Initialize DB
# --------------------------
def init_db():
    # Ensure DB file exists
    if not os.path.exists(DB_FILE):
        open(DB_FILE, "w").close()
