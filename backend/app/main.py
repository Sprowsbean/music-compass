"""
main.py — Music Compass API Entry Point
Run: uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import spotify, scores, analysis

app = FastAPI(title="Music Compass API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spotify.router)
app.include_router(scores.router)
app.include_router(analysis.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Music Compass API v2"}


@app.get("/health")
def health():
    return {"status": "healthy"}
