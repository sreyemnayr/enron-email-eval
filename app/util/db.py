from dotenv import load_dotenv
import os
from sqlmodel import create_engine, Session, select, func
from domain.models import Email, LLMBenchmark, ProcessedEmail, StockHistory

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def email_count():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        return session.exec(select(func.count(Email.filename))).one()


def processed_email_count():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        return session.exec(select(func.count(ProcessedEmail.id))).one()


def stock_history_count():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        return session.exec(select(func.count(StockHistory.date))).one()


def llm_benchmark_count():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        return session.exec(select(func.count(LLMBenchmark.id))).one()
