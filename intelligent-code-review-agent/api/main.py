"""FastAPI backend for the Code Review Agent GUI."""

import os
import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .routes import scan, report, config, guidelines, file_scan

app = FastAPI(
    title="Intelligent Code Review Agent",
    description="AI-powered code review with GUI",
    version="1.0.0",
)

# CORS for Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(scan.router, prefix="/api/scan", tags=["scan"])
app.include_router(report.router, prefix="/api/report", tags=["report"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(guidelines.router, prefix="/api/guidelines", tags=["guidelines"])
app.include_router(file_scan.router, prefix="/api/file-scan/", tags=["file-scan"])


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Serve Vue frontend in production
web_dist = project_root / "web" / "dist"
if web_dist.exists():
    app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")
