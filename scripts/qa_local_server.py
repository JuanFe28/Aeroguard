"""Servidor efímero para ensayar la batería web en SQLite; no es el destino PostgreSQL."""
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app.main import app

# La API expone un JSON en GET /; en este ensayo la raíz sirve el frontend.
app.router.routes[:] = [route for route in app.router.routes if getattr(route, 'path', None) != '/']
app.mount('/', StaticFiles(directory=Path(__file__).resolve().parents[1] / 'frontend', html=True), name='qa-frontend')
