import os
from pydantic_settings import BaseSettings
from typing import Literal, Optional
from functools import lru_cache


def get_secret_from_gcp(secret_id: str, project_id: str = "otb-dev-platform") -> Optional[str]:
    """
    Fetch a secret from GCP Secret Manager.

    Args:
        secret_id: The secret name in Secret Manager
        project_id: GCP project ID

    Returns:
        The secret value or None if not found
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Warning: Could not fetch secret {secret_id}: {e}")
        return None


@lru_cache()
def get_google_api_key() -> Optional[str]:
    """
    Get Google API key from environment or GCP Secret Manager.
    Cached to avoid repeated Secret Manager calls.
    """
    # First check environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key

    # Try to fetch from Secret Manager
    api_key = get_secret_from_gcp("otb_agents_GOOGLE_API_KEY")
    if api_key:
        # Set it as environment variable for google-genai to pick up
        os.environ["GOOGLE_API_KEY"] = api_key
        return api_key

    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AI Provider
    ai_provider: Literal["gemini", "openai"] = "gemini"
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4-turbo"

    # Google Cloud
    google_cloud_project: str = "otb-dev-platform"

    # BigQuery
    bq_dataset: str = "master"
    bq_table_tl: str = "northstar_master_combined_tl"
    bq_table_wh: str = "northstar_master_combined_wh"

    # Meta OAuth
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/auth/facebook/callback"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Observability
    fi_project_name: str = "agatha"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
settings = Settings()


# Model configuration for easy switching
MODEL_CONFIG = {
    "provider": settings.ai_provider,
    "gemini": {
        "model": settings.gemini_model,
    },
    "openai": {
        "model": settings.openai_model,
    }
}


def get_model_name() -> str:
    """Get the current model name based on provider setting."""
    provider = MODEL_CONFIG["provider"]
    return MODEL_CONFIG[provider]["model"]


def get_bq_table(tenant: Literal["tl", "wh"] = "tl") -> str:
    """Get the full BigQuery table path for a tenant."""
    table = settings.bq_table_tl if tenant == "tl" else settings.bq_table_wh
    return f"{settings.google_cloud_project}.{settings.bq_dataset}.{table}"
