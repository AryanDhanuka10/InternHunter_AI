"""
GET  /api/profile   — return current profile (from .env + any overrides)
POST /api/profile   — save profile overrides for this session
"""
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from internhunter import config as cfg

router = APIRouter()

# In-memory override store — survives the session, reset on server restart
# The source of truth is always .env; this layer lets you override at runtime
_overrides: dict = {}


class Profile(BaseModel):
    name:     str
    email:    str
    college:  str
    branch:   str
    year:     str
    skills:   List[str]
    github:   str
    linkedin: str
    resume_path: Optional[str] = None


def _current_profile() -> dict:
    """Merge .env config with any session overrides."""
    base = {
        "name":        cfg.USER_NAME,
        "email":       cfg.USER_EMAIL,
        "college":     cfg.USER_COLLEGE,
        "branch":      cfg.USER_BRANCH,
        "year":        cfg.USER_YEAR,
        "skills":      cfg.USER_SKILLS,
        "github":      cfg.USER_GITHUB,
        "linkedin":    cfg.USER_LINKEDIN,
        "resume_path": cfg.USER_RESUME_PATH,
    }
    base.update(_overrides)
    return base


@router.get("/", summary="Get current profile")
def get_profile():
    """Returns your profile loaded from .env, merged with any session overrides."""
    return _current_profile()


@router.post("/", summary="Save / update profile for this session")
def save_profile(profile: Profile):
    """
    Saves profile as a session override (survives until server restarts).
    To make permanent, update your .env file directly.
    """
    _overrides.update(profile.model_dump(exclude_none=True))
    return {
        "message": "Profile saved for this session",
        "note":    "To make permanent, update your .env file",
        "profile": _current_profile(),
    }


@router.delete("/overrides", summary="Clear session overrides, revert to .env")
def clear_overrides():
    _overrides.clear()
    return {"message": "Overrides cleared — reverted to .env values", "profile": _current_profile()}