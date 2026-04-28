"""
POST /api/actions/run-pipeline  — trigger full scrape → parse → store → email
GET  /api/actions/stats         — live DB stats
GET  /api/actions/logs          — last N lines from logs/daily.log
"""
import os, logging
from fastapi    import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic   import BaseModel

router  = APIRouter()
logger  = logging.getLogger(__name__)

# Track whether a pipeline run is already in progress (prevents double-trigger)
_running = {"active": False}


class PipelineResponse(BaseModel):
    status:        str
    message:       str
    summary:       dict = {}


@router.post("/run-pipeline", response_model=PipelineResponse,
             summary="Trigger the full internship pipeline")
def trigger_pipeline(background_tasks: BackgroundTasks, async_run: bool = False):
    """
    Runs scrape → parse → store → digest → email in one shot.

    - async_run=false (default): runs synchronously, returns full summary when done
    - async_run=true: returns immediately, pipeline runs in background
    """
    if _running["active"]:
        return PipelineResponse(
            status  = "skipped",
            message = "Pipeline already running — try again in a minute",
        )

    if async_run:
        background_tasks.add_task(_run_pipeline_task)
        return PipelineResponse(
            status  = "started",
            message = "Pipeline started in background — check /api/actions/logs for progress",
        )

    # Synchronous run — blocks until complete, returns full summary
    return _run_pipeline_task()


def _run_pipeline_task() -> PipelineResponse:
    from internhunter.scheduler import run as run_pipeline
    _running["active"] = True
    try:
        summary = run_pipeline()
        return PipelineResponse(
            status  = "success" if not summary.get("stages_fail") else "partial",
            message = (
                f"Pipeline complete — "
                f"{summary.get('inserted', 0)} new listings, "
                f"email {'sent' if summary.get('email_sent') else 'not sent'}"
            ),
            summary = summary,
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return PipelineResponse(status="error", message=str(e))
    finally:
        _running["active"] = False


@router.get("/stats", summary="Live database statistics")
def get_stats():
    """Returns counts from the live SQLite database."""
    from internhunter.database import init_db, get_stats as db_stats
    init_db()
    return db_stats()


@router.get("/logs", summary="Tail the daily log file")
def get_logs(lines: int = Query(50, ge=1, le=500, description="Number of lines to return")):
    """Returns the last N lines from logs/daily.log."""
    log_path = "logs/daily.log"
    if not os.path.exists(log_path):
        raise HTTPException(
            status_code = 404,
            detail      = "Log file not found — run the pipeline first"
        )
    with open(log_path, encoding="utf-8") as f:
        all_lines = f.readlines()
    tail = [l.rstrip() for l in all_lines[-lines:]]
    return {
        "log_path":    log_path,
        "total_lines": len(all_lines),
        "returned":    len(tail),
        "lines":       tail,
    }