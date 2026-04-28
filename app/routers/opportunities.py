"""
GET  /api/opportunities           — list opportunities with filters
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
import sqlite3

router = APIRouter()


class ApplyRequest(BaseModel):
    method: str = "cold_email"   # cold_email | company_site | referral
    notes:  str = ""


def _all_opportunities(limit: int) -> list[dict]:
    """Return all opportunities regardless of notified status — for the dashboard."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


@router.get("/", summary="List internship opportunities")
def list_opportunities(
    limit:       int           = Query(20,    ge=1, le=100),
    min_stipend: int           = Query(0,     ge=0),
    location:    Optional[str] = Query(None),
    role:        Optional[str] = Query(None),
    all:         bool          = Query(False, description="Include already-notified rows"),
):
    """
    Returns opportunities. By default returns only unnotified (new) ones.
    Pass ?all=true to see everything including already-sent ones.

        GET /api/opportunities/?all=true&limit=20
        GET /api/opportunities/?min_stipend=15000
        GET /api/opportunities/?location=bangalore
        GET /api/opportunities/?role=machine+learning
    """
    init_db()

    if location:
        return get_by_location(location, limit=limit)
    if role:
        return get_by_role(role, limit=limit)
    if min_stipend > 0:
        return get_by_stipend(min_amount=min_stipend, limit=limit)
    if all:
        return _all_opportunities(limit=limit)
    return get_new_opportunities(limit=limit)


@router.get("/{opp_id}", summary="Get a single opportunity by ID")
def get_opportunity(opp_id: int):
    init_db()
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