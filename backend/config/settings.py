import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly


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
    data_lookback_days: int = 30  # Days of data to fetch from BQ

    # LLM Reasoning Configuration
    enable_llm_reasoning: bool = True
    llm_timeout_seconds: float = 30.0
    gemini_api_key: str = ""

    # TODO: Add timezone and currency settings in future iteration
    # timezone: str = "America/Los_Angeles"
    # currency_field: str = "1"  # Default to no conversion

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
            data_lookback_days=int(os.getenv("DATA_LOOKBACK_DAYS", "30")),
            enable_llm_reasoning=os.getenv("ENABLE_LLM_REASONING", "true").lower() == "true",
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        )


settings = Settings.from_env()
