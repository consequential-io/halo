import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # AI Provider
    ai_provider: str = "gemini"  # gemini | openai
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4-turbo"

    # BigQuery
    gcp_project: str = "otb-dev-platform"
    bq_dataset: str = "master"

    # Data source
    data_source: str = "fixture"  # fixture | bq

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "gemini"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            gcp_project=os.getenv("GCP_PROJECT", "otb-dev-platform"),
            bq_dataset=os.getenv("BQ_DATASET", "master"),
            data_source=os.getenv("DATA_SOURCE", "fixture"),
        )


settings = Settings.from_env()
