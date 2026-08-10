from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    auto_create_schema: bool = False
    late_arrival_seconds: int = 300
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    chat_safety_salt: str = "sonoran-public-demo"

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
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            chat_safety_salt=os.getenv("CHAT_SAFETY_SALT", "sonoran-public-demo"),
        )
