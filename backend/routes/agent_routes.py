"""
Agent Routes - API endpoints for analysis, recommendations, and execution.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Annotated

from config.settings import settings
from controllers.agatha_controller import get_controller
from schemas.requests import AnalyzeRequest, RecommendRequest, ExecuteRequest
from schemas.responses import (
    AnalyzeResponse,
    RecommendResponse,
    ExecuteResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api", tags=["agents"])


async def verify_token(authorization: Annotated[str | None, Header()] = None) -> bool:
    """
    Verify bearer token for API access.

    In development mode, allows requests without token.
    In production, requires valid bearer token.
    """
    if settings.environment == "development":
        return True

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Use 'Bearer <token>'"
        )

    token = authorization.replace("Bearer ", "")
    if token != settings.api_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    return True


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def analyze(
    request: AnalyzeRequest,
    _: bool = Depends(verify_token)
) -> AnalyzeResponse:
    """
    Run anomaly analysis on ad data.

    Creates a new session and returns session_id for subsequent requests.
    """
    controller = get_controller()
    result = controller.run_analysis(
        tenant=request.tenant,
        days=request.days,
        source=request.source,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return AnalyzeResponse(**result)


@router.post(
    "/recommendations",
    response_model=RecommendResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def recommendations(
    request: RecommendRequest,
    _: bool = Depends(verify_token)
) -> RecommendResponse:
    """
    Generate recommendations from analysis results.

    Requires valid session_id from previous analyze call.
    """
    controller = get_controller()
    result = await controller.run_recommendations(
        session_id=request.session_id,
        enable_llm_reasoning=request.enable_llm_reasoning,
    )

    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=400, detail=result["error"])

    return RecommendResponse(**result)


@router.get(
    "/recommendations/{session_id}",
    response_model=RecommendResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_recommendations(
    session_id: str,
    _: bool = Depends(verify_token)
) -> RecommendResponse:
    """
    Get recommendations for an existing session.

    Returns cached recommendations if already generated.
    """
    controller = get_controller()
    session_state = controller.get_session_state(session_id)

    if session_state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if not session_state["has_recommendations"]:
        raise HTTPException(
            status_code=400,
            detail="No recommendations generated yet. POST to /api/recommendations first."
        )

    # Get from session
    session = controller.session_manager.get_session(session_id)
    if session is None or session.recommendations is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return RecommendResponse(
        session_id=session_id,
        recommendations=session.recommendations.get("recommendations", []),
        summary=session.recommendations.get("summary", {}),
    )


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def execute(
    request: ExecuteRequest,
    _: bool = Depends(verify_token)
) -> ExecuteResponse:
    """
    Execute approved recommendations.

    By default runs in dry_run mode (simulation).
    Set dry_run=False for actual execution (not recommended for hackathon).
    """
    controller = get_controller()
    result = await controller.run_execution(
        session_id=request.session_id,
        approved_ad_ids=request.approved_ad_ids,
        dry_run=request.dry_run,
    )

    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=400, detail=result["error"])

    return ExecuteResponse(**result)


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    _: bool = Depends(verify_token)
):
    """
    Get session state.

    Returns information about what steps have been completed.
    """
    controller = get_controller()
    state = controller.get_session_state(session_id)

    if state is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return state


@router.get("/tenants")
async def list_tenants(_: bool = Depends(verify_token)):
    """
    List available tenants.

    Returns configured tenants for the demo.
    """
    return {
        "tenants": [
            {"id": "TL", "name": "Third Love"},
            {"id": "WH", "name": "Whispering Homes"},
        ]
    }
