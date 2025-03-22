from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from pydantic import BaseModel


class BenchmarkSummary(BaseModel):
    summary: str
    is_discussing_stocks: bool


class Email(SQLModel, table=True):
    filename: str = Field(primary_key=True, unique=True, nullable=False, default="")
    message_id: str = Field(default="")
    date: datetime = Field(default=datetime.now(UTC))
    from_address: str = Field(default="")
    to_addresses: list[str] = Field(default=[], sa_column=Column(JSON))
    cc_addresses: list[str] = Field(default=[], sa_column=Column(JSON))
    bcc_addresses: list[str] = Field(default=[], sa_column=Column(JSON))
    subject: str = Field(default="")
    headers: dict[str, str] = Field(default={}, sa_column=Column(JSON))
    body: str = Field(default="")
    processed_emails: list["ProcessedEmail"] = Relationship(back_populates="email")


class ProcessedEmail(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email_id: str = Field(foreign_key="email.filename")
    email: Optional[Email] = Relationship(back_populates="processed_emails")
    benchmark_id: int | None = Field(default=None, foreign_key="llmbenchmark.id")
    benchmark: Optional["LLMBenchmark"] = Relationship(
        back_populates="processed_emails"
    )
    summary: str = Field(default="")
    stock_mentions: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = Field(default=None)


class LLMBenchmark(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(default="")
    model: str = Field(default="")
    subset: str = Field(default="")
    system_prompt: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_emails: list["ProcessedEmail"] = Relationship(back_populates="benchmark")


class StockHistory(SQLModel, table=True):
    date: datetime = Field(default=None, primary_key=True, unique=True, nullable=False)
    close: float = Field(default=0.0)
    high: float = Field(default=0.0)
    low: float = Field(default=0.0)
    volume: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
