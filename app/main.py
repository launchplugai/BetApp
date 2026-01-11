"""DNA Matrix API - FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import leading_light

app = FastAPI(
    title="DNA Matrix",
    description="Semantic identity management system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leading_light.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "dna-matrix"}


@app.get("/health")
async def health():
    """Health check for Railway."""
    return {"status": "healthy"}
