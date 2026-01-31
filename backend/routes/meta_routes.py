"""Meta Marketing API routes for ad and creative data."""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta-ads", tags=["meta-ads"])

META_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


async def _make_meta_request(
    endpoint: str,
    access_token: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make a request to the Meta Graph API.

    Args:
        endpoint: API endpoint (e.g., "/{ad_id}")
        access_token: Meta access token
        params: Additional query parameters

    Returns:
        API response data
    """
    url = f"{META_GRAPH_API_BASE}{endpoint}"
    request_params = {"access_token": access_token}
    if params:
        request_params.update(params)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=request_params)
        data = response.json()

        if "error" in data:
            error = data["error"]
            logger.error(f"Meta API error: {error}")
            raise HTTPException(
                status_code=error.get("code", 400),
                detail=error.get("message", "Meta API error")
            )

        return data


@router.get("/ads/{ad_id}")
async def get_ad_details(
    ad_id: str,
    authorization: str = Header(..., description="Bearer token from Meta OAuth")
) -> Dict[str, Any]:
    """
    Get ad details including creative information.

    Args:
        ad_id: The Meta ad ID
        authorization: Bearer token (from OAuth flow)

    Returns:
        Ad details with creative_id for preview fetch
    """
    # Extract token from "Bearer {token}" format
    if authorization.startswith("Bearer "):
        access_token = authorization[7:]
    else:
        access_token = authorization

    # Request ad details with creative info
    data = await _make_meta_request(
        f"/{ad_id}",
        access_token,
        params={
            "fields": "id,name,creative{id,image_url,thumbnail_url,video_id,object_story_spec},status,effective_status"
        }
    )

    # Transform response for frontend
    creative = data.get("creative", {})

    return {
        "data": {
            "ad_id": data.get("id"),
            "ad_name": data.get("name"),
            "status": data.get("status"),
            "effective_status": data.get("effective_status"),
            "creative_id": creative.get("id"),
            "image_url": creative.get("image_url") or creative.get("thumbnail_url"),
            "has_video": bool(creative.get("video_id")),
        }
    }


@router.get("/creative/{creative_id}/preview")
async def get_creative_preview(
    creative_id: str,
    ad_format: str = "DESKTOP_FEED_STANDARD",
    authorization: str = Header(..., description="Bearer token from Meta OAuth")
) -> Dict[str, Any]:
    """
    Get creative preview HTML for embedding.

    Args:
        creative_id: The Meta creative ID (from get_ad_details)
        ad_format: Preview format (DESKTOP_FEED_STANDARD, MOBILE_FEED_STANDARD, etc.)
        authorization: Bearer token

    Returns:
        Preview HTML that can be embedded in an iframe
    """
    if authorization.startswith("Bearer "):
        access_token = authorization[7:]
    else:
        access_token = authorization

    # Request creative preview
    data = await _make_meta_request(
        f"/{creative_id}/previews",
        access_token,
        params={"ad_format": ad_format}
    )

    previews = data.get("data", [])

    if not previews:
        return {
            "data": {
                "has_preview": False,
                "preview_html": None,
                "message": "No preview available for this creative"
            }
        }

    # Get the first preview
    preview = previews[0]

    return {
        "data": {
            "has_preview": True,
            "preview_html": preview.get("body"),
            "ad_format": ad_format,
        }
    }


@router.get("/accounts")
async def get_ad_accounts(
    authorization: str = Header(..., description="Bearer token from Meta OAuth")
) -> Dict[str, Any]:
    """
    Get list of ad accounts the user has access to.

    Args:
        authorization: Bearer token

    Returns:
        List of ad accounts
    """
    if authorization.startswith("Bearer "):
        access_token = authorization[7:]
    else:
        access_token = authorization

    # Get user's ad accounts
    data = await _make_meta_request(
        "/me/adaccounts",
        access_token,
        params={"fields": "id,name,account_status,currency,timezone_name"}
    )

    accounts = []
    for account in data.get("data", []):
        accounts.append({
            "id": account.get("id"),
            "name": account.get("name"),
            "status": account.get("account_status"),
            "currency": account.get("currency"),
            "timezone": account.get("timezone_name"),
        })

    return {"accounts": accounts}


@router.get("/accounts/{account_id}/ads")
async def get_account_ads(
    account_id: str,
    limit: int = 50,
    authorization: str = Header(..., description="Bearer token from Meta OAuth")
) -> Dict[str, Any]:
    """
    Get ads for a specific ad account.

    Args:
        account_id: The ad account ID (with or without 'act_' prefix)
        limit: Maximum number of ads to return
        authorization: Bearer token

    Returns:
        List of ads with performance data
    """
    if authorization.startswith("Bearer "):
        access_token = authorization[7:]
    else:
        access_token = authorization

    # Ensure account_id has act_ prefix
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    # Get ads with insights
    data = await _make_meta_request(
        f"/{account_id}/ads",
        access_token,
        params={
            "fields": "id,name,status,creative{id,thumbnail_url},insights{spend,impressions,clicks,ctr,cpc}",
            "limit": str(limit),
        }
    )

    ads = []
    for ad in data.get("data", []):
        insights = ad.get("insights", {}).get("data", [{}])[0] if ad.get("insights") else {}
        creative = ad.get("creative", {})

        ads.append({
            "id": ad.get("id"),
            "name": ad.get("name"),
            "status": ad.get("status"),
            "thumbnail_url": creative.get("thumbnail_url"),
            "creative_id": creative.get("id"),
            "spend": float(insights.get("spend", 0)),
            "impressions": int(insights.get("impressions", 0)),
            "clicks": int(insights.get("clicks", 0)),
            "ctr": float(insights.get("ctr", 0)),
            "cpc": float(insights.get("cpc", 0)),
        })

    return {"ads": ads, "count": len(ads)}
