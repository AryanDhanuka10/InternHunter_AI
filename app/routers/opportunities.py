"""
GET  /api/opportunities           — list new opportunities with filters
GET  /api/opportunities/{id}      — get one opportunity by ID
POST /api/opportunities/{id}/apply — mark as applied
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from internhunter.database import (
    init_db, get_new_opportunities, get_by_stipend,
    get_by_location, get_by_role, mark_applied, get_conn
)

router = APIRouter()


class ApplyRequest(BaseModel):
    method: str = "cold_email"   # cold_email | company_site | referral
    notes:  str = ""


@router.get("/", summary="List new internship opportunities")
def list_opportunities(
    limit:      int            = Query(20,  ge=1, le=100, description="Max results"),
    min_stipend:int            = Query(0,   ge=0,         description="Minimum stipend in ₹/month"),
    location:   Optional[str]  = Query(None,              description="Filter by city e.g. bangalore"),
    role:       Optional[str]  = Query(None,              description="Filter by role keyword e.g. ml"),
):
    """
    Returns new (unnotified) opportunities. Combine filters freely:

        GET /api/opportunities?min_stipend=15000&location=bangalore
        GET /api/opportunities?role=machine+learning&limit=10
    """
    init_db()

    if location:
        return get_by_location(location, limit=limit)
    if role:
        return get_by_role(role, limit=limit)
    if min_stipend > 0:
        return get_by_stipend(min_amount=min_stipend, limit=limit)
    return get_new_opportunities(limit=limit)


@router.get("/{opp_id}", summary="Get a single opportunity by ID")
def get_opportunity(opp_id: int):
    init_db()
    import sqlite3
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM opportunities WHERE id = ?", (opp_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Opportunity {opp_id} not found")
    return dict(row)


@router.post("/{opp_id}/apply", summary="Mark an opportunity as applied")
def apply_to_opportunity(opp_id: int, body: ApplyRequest):
    """
    Logs your application and updates status to 'applied'.
    method: cold_email | company_site | referral
    """
    init_db()
    try:
        mark_applied(opp_id, method=body.method, notes=body.notes)
        return {
            "status":  "applied",
            "opp_id":  opp_id,
            "method":  body.method,
            "message": f"Marked opportunity {opp_id} as applied via {body.method}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))