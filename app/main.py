"""
FastAPI app — run: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import opportunities, profile, actions

app = FastAPI(title="InternHunter API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(profile.router,       prefix="/api/profile",       tags=["profile"])
app.include_router(actions.router,       prefix="/api/actions",        tags=["actions"])

@app.get("/")
def root():
    return {"status": "InternHunter is running 🚀"}
