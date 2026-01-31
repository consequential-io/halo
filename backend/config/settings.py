import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # AI Provider
    ai_provider: str = "gemini"  # gemini | openai
    gemini_model: str = "gemini-3.0-flash"
    openai_model: str = "gpt-4-turbo"

    # BigQuery
    gcp_project: str = "otb-dev-platform"
    bq_dataset: str = "master"

    # Data source
    data_source: str = "fixture"  # fixture | bq
    data_lookback_days: int = 30  # Days of data to fetch from BQ

    # TODO: Add timezone and currency settings in future iteration
    # timezone: str = "America/Los_Angeles"
    # currency_field: str = "1"  # Default to no conversion

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "gemini"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.0-flash"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            gcp_project=os.getenv("GCP_PROJECT", "otb-dev-platform"),
            bq_dataset=os.getenv("BQ_DATASET", "master"),
            data_source=os.getenv("DATA_SOURCE", "fixture"),
            data_lookback_days=int(os.getenv("DATA_LOOKBACK_DAYS", "30")),
        )


settings = Settings.from_env()
