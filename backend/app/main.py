from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router

app = FastAPI(
    title="Goose API Server",
    description="FastAPI Backend for Goose Stock Tracker",
    version="0.1.0",
)

# Enable CORS for frontend clients (Angular / local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Goose API Server Running", "docs": "/docs"}
