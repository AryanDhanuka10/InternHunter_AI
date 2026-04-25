from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Profile(BaseModel):
    name: str
    email: str
    college: str
    branch: str
    year: str
    skills: List[str]
    github: str
    linkedin: str

_profile_store = {}

@router.post("/")
def save_profile(profile: Profile):
    _profile_store.update(profile.dict())
    return {"message": "Profile saved", "profile": _profile_store}

@router.get("/")
def get_profile():
    return _profile_store
