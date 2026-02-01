"""Agent API routes."""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from schemas.requests import AnalyzeRequest, RecommendRequest, ExecuteRequest

logger = logging.getLogger(__name__)
from controllers.agatha_controller import AgathaController

router = APIRouter(prefix="/api", tags=["agents"])

# Global controller instance
controller = AgathaController()


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Analyze ad performance and classify each ad.

    Returns classifications (GOOD/OK/WARNING/BAD/WAIT) with chain-of-thought reasoning.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[REQUEST] id={request_id} endpoint=/analyze ads={len(request.ads)} avg_roas={request.account_avg_roas}")
    try:
        ads = [ad.model_dump() for ad in request.ads]
        result = await controller.analyze(
            account_avg_roas=request.account_avg_roas,
            ads=ads
        )
        logger.info(f"[RESPONSE] id={request_id} status=success ads={len(result['results'])}")
        return result
    except Exception as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
async def recommend(request: RecommendRequest):
    """
    Generate budget recommendations from analysis results.

    Uses session_id to retrieve cached analysis, or accepts direct analysis_results.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[REQUEST] id={request_id} endpoint=/recommend session_id={request.session_id}")
    try:
        result = await controller.recommend(
            session_id=request.session_id,
            analysis_results=request.analysis_results
        )
        logger.info(f"[RESPONSE] id={request_id} status=success recommendations={len(result['recommendations'])}")
        return result
    except ValueError as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute(request: ExecuteRequest):
    """
    Execute approved recommendations.

    By default runs in mock mode (no real API calls).
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[REQUEST] id={request_id} endpoint=/execute session_id={request.session_id} mock_mode={request.mock_mode}")
    try:
        result = await controller.execute(
            session_id=request.session_id,
            recommendations=request.recommendations,
            approved_ads=request.approved_ads,
            mock_mode=request.mock_mode
        )
        logger.info(f"[RESPONSE] id={request_id} status=success")
        return result
    except ValueError as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline")
async def run_pipeline(request: AnalyzeRequest):
    """
    Run the full Analyze → Recommend → Execute pipeline in one call.

    Returns analysis, recommendations, and execution results.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[REQUEST] id={request_id} endpoint=/pipeline ads={len(request.ads)} avg_roas={request.account_avg_roas}")
    try:
        ads = [ad.model_dump() for ad in request.ads]
        result = await controller.run_full_pipeline(
            account_avg_roas=request.account_avg_roas,
            ads=ads,
            mock_mode=True  # Always mock for now
        )
        logger.info(f"[RESPONSE] id={request_id} status=success session_id={result.get('session_id')}")
        return result
    except Exception as e:
        logger.error(f"[RESPONSE] id={request_id} status=error error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixture")
async def get_fixture():
    """
    Get the test fixture data (for demo/testing).
    """
    from helpers.tools import get_fixture_with_expected

    try:
        data = get_fixture_with_expected()
        return {
            "account_avg_roas": data["account_avg_roas"],
            "total_spend": data.get("total_spend"),
            "date_range": data.get("date_range"),
            "ads": [
                {
                    "ad_name": ad["ad_name"],
                    "ad_provider": ad["ad_provider"],
                    "spend": ad["spend"],
                    "roas": ad["roas"],
                    "days_active": ad["days_active"],
                }
                for ad in data["ads"]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
