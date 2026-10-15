"""Feedback API routes."""

from fastapi import APIRouter, HTTPException
from app.schemas import ErrorResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", responses={501: {"model": ErrorResponse}})
async def submit_feedback() -> dict:
    """
    Submit user feedback (like, dislike, watched, more like this).

    Not yet implemented - feedback system coming in Milestone 9.
    """
    raise HTTPException(
        status_code=501,
        detail="Feedback not yet implemented. Coming in Milestone 9.",
    )