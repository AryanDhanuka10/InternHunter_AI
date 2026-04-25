from fastapi import APIRouter
from internhunter.database import init_db, get_new_opportunities

router = APIRouter()

@router.get("/")
def list_opportunities(limit: int = 20):
    init_db()
    return get_new_opportunities(limit)
