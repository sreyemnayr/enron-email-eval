from enum import Enum
import json
import shutil
import zipfile
from sqlalchemy import func, delete
import typer
from pathlib import Path
from util.fileparser import parse_email_file
from rich.prompt import Prompt, IntPrompt
from rich.progress import track
from rich.panel import Panel
from rich.text import Text
from sqlmodel import create_engine, Session
from util.db import (
    email_count,
    processed_email_count,
    stock_history_count,
    llm_benchmark_count,
)

from init_db import init_db
import csv
from domain.models import (
    StockHistory,
    LLMBenchmark,
    Email,
    ProcessedEmail,
    BenchmarkSummary,
)
from sqlmodel import select, and_
from datetime import datetime, UTC
from rich import print
from util.tgi import check_health, check_ollama
from typing_extensions import Annotated
from dotenv import load_dotenv
import os

from ollama import ChatResponse, Client, Options

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_ID = os.getenv("MODEL_ID")

engine = create_engine(DATABASE_URL)

DEFAULT_SYSTEM_PROMPT = "You are an investigator for the SEC. You specialize in securities fraud. Your job is analyzing emails to determine their nature and whether or not they are discussing stocks, the stock market, stock tickers, stock prices, etc. You will provide a brief (1 sentence) summary of the email's subject matter and flag your best evaluation of whether the email is discussing stocks, stock prices, etc. Your summary should be brief and to the point, without any preamble or conclusion."

app = typer.Typer()


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        menu()


@app.command()
def reset_database():
    init_db(drop_all=True)
    print("Database tables dropped and recreated")
    menu()


@app.command()
def init_emails():

    emails = []
    files = [f for f in Path("/email-data/maildir").glob("**/*") if f.is_file()]

    with Session(engine) as session:
        for file in track(files, description="Parsing emails"):
            try:
                if email := parse_email_file(file):
                    emails.append(email)
                    session.add(email)
            except Exception as e:
                print(f"Error parsing email file {file}: {e}")
        print(f"Parsed {len(emails)} of {len(files)} emails")
        print("Committing emails to database")
        session.commit()
        print("Emails committed to database")

    menu()


@app.command()
def init_stock_prices():
    print("Initializing stock price database")
    stock_prices = []
    with Session(engine) as session:
        print("Removing existing stock prices")
        session.exec(delete(StockHistory))
        session.commit()
        print("Removing existing stock prices complete")

        with open("/stock-data/stock_history.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in track(reader, description="Parsing stock prices"):
                stock_price = StockHistory(
                    date=datetime.strptime(row["Date"], "%m/%d/%Y"),
                    close=float(row["Close"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    volume=float(row["Volume"] if row["Volume"] != "N/A" else 0),
                )
                stock_prices.append(stock_price)
                session.add(stock_price)
        print(f"Parsed {len(stock_prices)} stock prices")
        print("Committing stock prices to database")
        session.commit()
        print("Stock prices committed to database")

    menu()


class BenchmarkDOW(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"
    ALL = "ALL"


class BenchmarkPeriod(str, Enum):
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    ALL = "ALL"


@app.command()
def new_benchmark(
    name: Annotated[
        str, typer.Option(prompt="Name of the benchmark (ex. DeepSeekV3 Tuesdays)")
    ] = None,
    system_prompt: Annotated[
        str, typer.Option(prompt="System prompt for the benchmark")
    ] = None,
    num: Annotated[
        int,
        typer.Option(prompt="Benchmark [num] emails per [per] (-1 = ALL)", min=-1),
    ] = None,
    dow: Annotated[
        BenchmarkDOW,
        typer.Option("--dow", prompt="Day of week to benchmark"),
    ] = None,
    per: Annotated[
        BenchmarkPeriod,
        typer.Option("--per", prompt="Period to benchmark"),
    ] = None,
):
    confirmed = False
    while not confirmed:
        if not name:
            name = Prompt.ask(
                "Name of the benchmark (ex. DeepSeekV3 Tuesdays)",
                default=f"Benchmark with {MODEL_ID}",
            )
        if not system_prompt:
            system_prompt = Prompt.ask(
                "System prompt for the benchmark", default=DEFAULT_SYSTEM_PROMPT
            )
        if not num:
            num = IntPrompt.ask("Number of emails per period (-1 = ALL)", default=-1)
        if not per:
            per = Prompt.ask(
                "Period to benchmark",
                choices=[per.value for per in BenchmarkPeriod],
                default=BenchmarkPeriod.DAY,
            )
        if not dow:
            dow = Prompt.ask(
                "Day of week to benchmark",
                choices=[dow.value for dow in BenchmarkDOW],
                default=BenchmarkDOW.ALL,
            )
        print(f"Benchmark parameters:")
        print(f"Name: {name}")
        print(f"System prompt: {system_prompt}")
        print(f"Number of emails per period: {num}")
        print(f"Period to benchmark: {per}")
        print(f"Day of week to benchmark: {dow}")
        print(f"Are you sure you want to create this benchmark?")
        confirmed_str = Prompt.ask("Confirm benchmark", default="y", choices=["y", "n"])
        confirmed = confirmed_str == "y"
        if not confirmed:
            name = None
            system_prompt = None
            num = None
            per = None
            dow = None

    with Session(engine) as session:
        benchmark = LLMBenchmark(
            name=name,
            system_prompt=system_prompt,
            model=MODEL_ID,
            subset=f"{num} per {str(per)} ({str(dow)})",
        )
        session.add(benchmark)
        session.commit()
        print(f"Benchmark created with id {benchmark.id}")
        print(f"Fetching emails for benchmark")

        if per == BenchmarkPeriod.ALL or num <= 0:
            query = select(Email).where(Email.date.is_not(None))
        else:
            if per == BenchmarkPeriod.HOUR:
                partition_by = (
                    func.date_part("hour", Email.date),
                    func.date(Email.date),
                )
            elif per == BenchmarkPeriod.WEEK:
                partition_by = (
                    func.date_part("week", Email.date),
                    func.date_part("year", Email.date),
                )
            elif per == BenchmarkPeriod.MONTH:
                partition_by = (
                    func.date_part("month", Email.date),
                    func.date_part("year", Email.date),
                )
            else:  # DAY
                partition_by = func.date(Email.date)

            window = (
                func.row_number()
                .over(partition_by=partition_by, order_by=Email.date)
                .label("row_number")
            )

            subq = (
                select(Email.filename, Email.date, window)
                .group_by(Email.filename)
                .subquery("sq")
            )

            query = select(Email).join(
                subq, and_(subq.c.row_number <= num, Email.filename == subq.c.filename)
            )

        if dow != BenchmarkDOW.ALL:
            if dow == BenchmarkDOW.SUNDAY:
                query = query.where(func.date_part("dow", Email.date) == 0)
            elif dow == BenchmarkDOW.MONDAY:
                query = query.where(func.date_part("dow", Email.date) == 1)
            elif dow == BenchmarkDOW.TUESDAY:
                query = query.where(func.date_part("dow", Email.date) == 2)
            elif dow == BenchmarkDOW.WEDNESDAY:
                query = query.where(func.date_part("dow", Email.date) == 3)
            elif dow == BenchmarkDOW.THURSDAY:
                query = query.where(func.date_part("dow", Email.date) == 4)
            elif dow == BenchmarkDOW.FRIDAY:
                query = query.where(func.date_part("dow", Email.date) == 5)
            elif dow == BenchmarkDOW.SATURDAY:
                query = query.where(func.date_part("dow", Email.date) == 6)

        emails = session.exec(query).all()

        print(
            f"Found {len(emails)} emails in subset ({num} per {str(per)} ({str(dow)}))"
        )
        print(f"Creating benchmark entries for {len(emails)} emails")
        for email in track(emails, description="Creating benchmark entries"):

            benchmark_entry = ProcessedEmail(
                email_id=email.filename,
                benchmark_id=benchmark.id,
            )
            client = Client(host="http://host.docker.internal:11434")
            chat = client.chat

            done = False
            while not done:
                print(f"Processing email {email.filename}")
                try:
                    response: ChatResponse = chat(
                        model=MODEL_ID,
                        messages=[
                            {
                                "role": "system",
                                "content": benchmark.system_prompt,
                            },
                            {
                                "role": "user",
                                "content": f"Analyze the following email: `{email.body}`",
                                # and respond in this format: {BenchmarkSummary.model_json_schema()}",
                            },
                        ],
                        format=BenchmarkSummary.model_json_schema(),
                        # options=Options(
                        #     num_ctx=16384,
                        # ),
                    )
                    summary = BenchmarkSummary.model_validate_json(
                        response["message"]["content"]
                    )
                    benchmark_entry.summary = summary.summary
                    benchmark_entry.stock_mentions = summary.is_discussing_stocks
                    benchmark_entry.processed_at = datetime.now(UTC)

                    print(
                        f"[{'red' if benchmark_entry.stock_mentions else 'cyan'}] {benchmark_entry.summary}[/{'red' if benchmark_entry.stock_mentions else 'cyan'}]"
                    )

                    session.add(benchmark_entry)
                    session.commit()
                    done = True
                except Exception as e:
                    print(f"Error processing email {email.filename}: {e}")
                    print(f"Retrying...")
                    done = False

        session.commit()


@app.command()
def export_benchmark(
    benchmark_id: Annotated[int, typer.Option("--id", prompt="Benchmark ID")] = None,
):
    with Session(engine) as session:
        if not benchmark_id:
            benchmarks = session.exec(select(LLMBenchmark)).all()
            for benchmark in benchmarks:
                print(
                    f"[cyan][b]{benchmark.id}:[/b] {benchmark.name} - {benchmark.model} - ({benchmark.subset})[/cyan]"
                )
            benchmark_id = IntPrompt.ask(
                "Benchmark ID",
                choices=[str(benchmark.id) for benchmark in benchmarks],
            )

        benchmark = session.exec(
            select(LLMBenchmark).where(LLMBenchmark.id == benchmark_id)
        ).one()

        print(
            f"Exporting benchmark {benchmark.id} - {benchmark.name} - {benchmark.model} - ({benchmark.subset})"
        )

        benchmark_entries = session.exec(
            select(ProcessedEmail).where(ProcessedEmail.benchmark_id == benchmark_id)
        ).all()

        benchmark_entries.sort(key=lambda x: x.email.date)

        print(f"Exporting {len(benchmark_entries)} benchmark entries")

        benchmark_dir = f"/results/{benchmark.id}_{benchmark.model}"

        os.makedirs(f"{benchmark_dir}/emails", exist_ok=True)

        with open(f"{benchmark_dir}/benchmark_info.json", "w") as f:
            json.dump(benchmark.model_dump_json(), f)

        with open(f"{benchmark_dir}/benchmark.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["sender", "recipients", "date", "summary", "price", "stock_discussion"]
            )
            for benchmark_entry in benchmark_entries:
                stock_price = session.exec(
                    select(StockHistory)
                    .where(StockHistory.date <= benchmark_entry.email.date)
                    .order_by(StockHistory.date.desc())
                ).first()

                recipients = [
                    *benchmark_entry.email.to_addresses,
                    *benchmark_entry.email.cc_addresses,
                    *benchmark_entry.email.bcc_addresses,
                ]
                if not recipients:
                    recipients = [benchmark_entry.email.from_address]

                writer.writerow(
                    [
                        benchmark_entry.email.from_address,
                        ";".join(recipients),
                        benchmark_entry.email.date,
                        benchmark_entry.summary,
                        stock_price.close,
                        benchmark_entry.stock_mentions,
                    ]
                )

                file_name = benchmark_entry.email.filename
                file_path = f"{benchmark_dir}/emails/{file_name}"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                shutil.copy(f"/email-data/maildir/{file_name}", file_path)

            # Zip the emails, then delete the directory
            with zipfile.ZipFile(f"{benchmark_dir}/emails.zip", "w") as zipf:
                for file in Path(f"{benchmark_dir}/emails").glob("**/*"):
                    zipf.write(file, file.relative_to(Path(f"{benchmark_dir}/emails")))
            shutil.rmtree(f"{benchmark_dir}/emails")

        print(
            f"Exported benchmark {benchmark.id} - {benchmark.name} - {benchmark.model} - ({benchmark.subset}) to {benchmark_dir}"
        )


@app.command()
def menu():
    menu_choices = {
        "NUKE": [reset_database, "Reset database"],
    }
    email_count_n = email_count()
    menu_choices["e"] = [
        init_emails,
        f"{'Re-initialize' if email_count_n > 0 else 'Initialize'} emails in database ({email_count_n} in db)",
    ]

    stock_history_count_n = stock_history_count()
    menu_choices["s"] = [
        init_stock_prices,
        f"{'Re-initialize' if stock_history_count_n > 0 else 'Initialize'} stock price database ({stock_history_count_n} in db)",
    ]

    if check_ollama() and email_count_n > 0:
        menu_choices["n"] = [new_benchmark, f"Create new benchmark for {MODEL_ID}"]

    llm_benchmark_count_n = llm_benchmark_count()
    if llm_benchmark_count_n > 0:
        menu_choices["b"] = [
            export_benchmark,
            f"Export benchmark results ({llm_benchmark_count_n} benchmarks)",
        ]

    menu_choices["x"] = [exit, "Exit"]

    status = "[green]ONLINE[/green]" if check_ollama() else "[red]OFFLINE[/red]"

    panel = Panel(
        "\n".join([f"[b]{key}:[/b] {value[1]}" for key, value in menu_choices.items()]),
        title="Enron Email LLM Benchmark",
        subtitle=f"{MODEL_ID} ── [b]Ollama[/b] {status} ── {email_count_n} [b]Emails[/b] ",
        border_style="magenta",
    )
    print(panel)

    choice = Prompt.ask(
        "Please select an option",
        choices=menu_choices.keys(),
    )
    menu_choices[choice][0]()


if __name__ == "__main__":
    app()
