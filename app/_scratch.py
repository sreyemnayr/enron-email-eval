from enum import Enum
from sqlalchemy import func
import typer
from pathlib import Path
from util.fileparser import parse_email_file
from rich.prompt import Prompt
from rich.progress import track
from rich.panel import Panel
from rich.text import Text
from sqlmodel import create_engine, Session, and_, delete


from init_db import init_db
import csv
from domain.models import StockHistory, LLMBenchmark, Email, ProcessedEmail
from sqlmodel import select
from datetime import datetime
from rich import print
from util.tgi import check_health
from typing_extensions import Annotated
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
with Session(engine) as session:

    # window = func.row_number().over(
    #             partition_by=(func.date_part('week', Email.date), func.date_part('year', Email.date)),
    #             order_by=Email.date
    #         ).label('row_number')

    # subq = select(Email.filename, Email.date, window).group_by(Email.filename).subquery('t2')

    # query = select(Email).join(subq, and_(
    #     subq.c.row_number == 1,
    #     Email.filename == subq.c.filename
    # ))
    # processed_emails = session.exec(select(ProcessedEmail).where(ProcessedEmail.summary != "")).all()
    # for processed_email in processed_emails:
    #     print(processed_email.summary)
    # stock_histories = session.exec(select(StockHistory)).all()
    # for stock_history in stock_histories:
    #     print(stock_history.date)

    # session.exec(delete(LLMBenchmark))
    # session.commit()
    histories = session.exec(select(StockHistory)).all()
    for history in histories:
        print(history.date, history.close)
# You are an investigator for the SEC. You specialize in securities fraud. Your job is analyzing emails to determine their nature and whether or not they are discussing stocks, stock prices, etc. You will provide a brief (1-2 sentences) summary of the email and your best evaluation of whether or not the email is discussing stocks, stock prices, etc.
