"""
app/main.py — InternHunter FastAPI application.

Endpoints:
  GET  /                          health check
  GET  /health                    detailed health + DB stats
  GET  /api/opportunities         list new opportunities (filterable)
  GET  /api/opportunities/{id}    get single opportunity
  POST /api/opportunities/{id}/apply  mark as applied
  GET  /api/profile               get current profile
  POST /api/profile               save / update profile
  POST /api/actions/run-pipeline  trigger full pipeline
  GET  /api/actions/stats         DB summary stats
  GET  /docs                      Swagger UI (auto-generated)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import opportunities, profile, actions

app = FastAPI(
    title       = "InternHunter API",
    description = "Automated internship discovery for B.Tech students",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(profile.router,       prefix="/api/profile",       tags=["profile"])
app.include_router(actions.router,       prefix="/api/actions",        tags=["actions"])


@app.get("/", tags=["health"])
def root():
    return {
        "status":  "running",
        "app":     "InternHunter API",
        "version": "1.0.0",
        "docs":    "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    """Detailed health check — confirms DB is reachable and returns live stats."""
    from internhunter.database import init_db, get_stats
    try:
        init_db()
        stats = get_stats()
        return {"status": "healthy", "database": "ok", "stats": stats}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}