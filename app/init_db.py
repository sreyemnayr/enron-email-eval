from sqlmodel import SQLModel, create_engine, Session
from domain.models import *
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/enron")

engine = create_engine(DATABASE_URL, echo=True)


def init_db(drop_all=False):
    """Initialize the database, creating all tables if they don't exist."""
    print("Creating database engine...")
    engine = create_engine(DATABASE_URL, echo=True)

    print("Enabling pgvector extension...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    print("Creating all tables...")
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("Database initialization completed!")


def get_session():
    with Session(engine) as session:
        yield session


if __name__ == "__main__":
    init_db()
