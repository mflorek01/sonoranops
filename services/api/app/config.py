from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    auto_create_schema: bool = False
    late_arrival_seconds: int = 300
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    @classmethod
    def from_environment(cls) -> Settings:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://sonoran:change-me@localhost:5432/sonoran_ops",
        )
        cors_origins = tuple(
            origin.strip().rstrip("/")
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        )
        return cls(
            database_url=database_url,
            auto_create_schema=os.getenv("AUTO_CREATE_SCHEMA", "false").lower() == "true",
            cors_origins=cors_origins,
        )
