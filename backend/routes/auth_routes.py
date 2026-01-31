"""
Auth Routes - Meta OAuth endpoints.
"""

import urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class MetaLoginResponse(BaseModel):
    """Response with OAuth URL."""
    oauth_url: str


class MetaCallbackParams(BaseModel):
    """Callback parameters from Meta OAuth."""
    code: str | None = None
    error: str | None = None
    error_reason: str | None = None


@router.get("/meta/login")
async def meta_login_redirect():
    """
    Direct browser redirect to Meta OAuth.

    Use this endpoint directly in browser for testing.
    """
    if not settings.meta_app_id or not settings.meta_redirect_uri:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=not_configured")

    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "scope": "ads_read,ads_management",
        "response_type": "code",
        "state": "agatha_login",
    }
    oauth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=oauth_url)


@router.post("/meta/login", response_model=MetaLoginResponse)
async def meta_login() -> MetaLoginResponse:
    """
    Initiate Meta OAuth login (for frontend).

    Returns the OAuth URL to redirect the user to.
    In demo mode (no redirect URI), returns empty URL.
    """
    if not settings.meta_app_id or not settings.meta_redirect_uri:
        # Demo mode - return empty URL, frontend will use demo login
        return MetaLoginResponse(oauth_url="")

    # Build OAuth URL
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "scope": "ads_read,ads_management",
        "response_type": "code",
        "state": "agatha_login",  # In production, use a secure random state
    }

    oauth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urllib.parse.urlencode(params)}"

    return MetaLoginResponse(oauth_url=oauth_url)


@router.get("/meta/callback")
async def meta_callback(
    code: str | None = None,
    error: str | None = None,
    error_reason: str | None = None,
    state: str | None = None,
):
    """
    Handle Meta OAuth callback.

    Exchanges auth code for access token and redirects to frontend.
    """
    if error:
        # Redirect to frontend with error
        error_params = urllib.parse.urlencode({
            "error": error,
            "error_reason": error_reason or "unknown",
        })
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?{error_params}"
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for access token
    # For hackathon, we'll skip actual token exchange and just redirect
    # In production, you would call the Meta Graph API here

    # For now, redirect to frontend with success
    # The frontend will use the API_TOKEN for bearer auth
    return RedirectResponse(
        url=f"{settings.frontend_url}/dashboard?auth=success"
    )


@router.get("/status")
async def auth_status():
    """
    Check auth configuration status.

    Returns configuration state (not secrets).
    """
    return {
        "meta_app_id_configured": bool(settings.meta_app_id),
        "meta_redirect_uri_configured": bool(settings.meta_redirect_uri),
        "api_token_configured": bool(settings.api_token),
        "environment": settings.environment,
    }
