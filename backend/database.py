import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON,Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# Default local SQLite database inside data/ folder; drop-in compatible with PostgreSQL/PostGIS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_DB_URL = f"sqlite:///{os.path.join(DATA_DIR, 'freedom_auditor.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class HazardAudit(Base):
    __tablename__ = "hazard_audits"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(32), unique=True, index=True, nullable=False)
    reporter_name = Column(String(120), default="Anonymous Citizen")
    mobility_profile = Column(String(80), default="Pedestrian")
    location_label = Column(String(255), default="Unlabeled Road Segment")
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)

    # AI Computer Vision outputs
    severity_level = Column(String(20), nullable=False)  # GREEN, YELLOW, RED
    accessibility_score = Column(Integer, default=50)
    severity_score = Column(Float, default=0.0)
    detected_hazards = Column(JSON, default=list)         # List of bounding boxes & labels
    original_image_path = Column(String(500), nullable=False)
    annotated_image_path = Column(String(500), nullable=False)

    # Mobility & Vehicle safety guidance
    wheelchair_safe = Column(String(20), default="UNKNOWN")
    elder_safe = Column(String(20), default="UNKNOWN")
    vehicle_advisory = Column(Text, default="")
    reroute_suggestion = Column(Text, default="")
    voice_alert_text = Column(Text, default="")

    # Dual-Track Resolution Workflow
    action_track = Column(String(50), default="CITIZEN_QUICK_FIX")  # MUNICIPAL_ESCALATION vs CITIZEN_QUICK_FIX
    ticket_status = Column(String(30), default="OPEN")              # OPEN, CLAIMED, ESCALATED, RESOLVED
    claimed_by = Column(String(120), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    municipal_pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
