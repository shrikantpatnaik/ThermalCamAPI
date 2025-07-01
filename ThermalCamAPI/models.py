import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import Column, ARRAY, DECIMAL, String
from sqlmodel import SQLModel, Field


class CamData(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    min: Decimal = Field(default=0, max_digits=5, decimal_places=2)
    max: Decimal = Field(default=0, max_digits=5, decimal_places=2)
    data: List[Decimal] = Field(sa_column=Column(ARRAY(DECIMAL)))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

    class Config:
        arbitrary_types_allowed = True

class CamDataWithoutData(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    min: Decimal = Field(default=0, max_digits=5, decimal_places=2)
    max: Decimal = Field(default=0, max_digits=5, decimal_places=2)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)


class APIKeys(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column("name", String, unique=True))
    key: str = Field(sa_column=Column("key", String, unique=True))
    disabled: bool = Field(default=False, nullable=False)
    admin: bool = Field(default=False, nullable=False)