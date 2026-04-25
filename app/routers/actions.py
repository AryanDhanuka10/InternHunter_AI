from fastapi import APIRouter
from internhunter.scheduler import run as run_pipeline

router = APIRouter()

@router.post("/run-pipeline")
def trigger_pipeline():
    try:
        run_pipeline()
        return {"status": "success", "message": "Pipeline ran successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
