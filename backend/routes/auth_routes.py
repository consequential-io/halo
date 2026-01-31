"""Meta OAuth routes."""

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
import httpx

from config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/facebook")
async def facebook_login(redirectTo: str = Query(default="/")):
    """
    Redirect to Facebook OAuth consent screen.

    Args:
        redirectTo: URL to redirect after successful auth
    """
    if not settings.meta_app_id:
        return {"error": "META_APP_ID not configured"}

    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={settings.meta_app_id}"
        f"&redirect_uri={settings.meta_redirect_uri}"
        f"&scope=ads_read,ads_management,business_management"
        f"&state={redirectTo}"
    )
    return RedirectResponse(url=oauth_url)


@router.get("/facebook/callback")
async def facebook_callback(code: str, state: str = "/"):
    """
    Handle OAuth callback, exchange code for token.

    Args:
        code: Authorization code from Facebook
        state: Return URL (passed in initial request)
    """
    if not settings.meta_app_id or not settings.meta_app_secret:
        return {"error": "Meta OAuth not configured"}

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": settings.meta_redirect_uri,
                "code": code
            }
        )
        token_data = token_response.json()

        if "error" in token_data:
            return {"error": token_data.get("error", {}).get("message", "Token exchange failed")}

        access_token = token_data.get("access_token")

        # Get long-lived token (optional but recommended)
        long_token_response = await client.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": access_token
            }
        )
        long_token_data = long_token_response.json()

        final_token = long_token_data.get("access_token", access_token)

        # For hackathon: redirect to frontend with token
        # In production: store encrypted in database
        redirect_url = f"{state}?token={final_token}" if "?" not in state else f"{state}&token={final_token}"
        return RedirectResponse(url=redirect_url)


@router.get("/status")
async def auth_status():
    """Check OAuth configuration status."""
    return {
        "meta_configured": bool(settings.meta_app_id and settings.meta_app_secret),
        "redirect_uri": settings.meta_redirect_uri,
    }
