"""
epopy - Async Python client for EPO Open Patent Services (OPS) API.

This library provides an async API for searching patents, retrieving
bibliographic data, downloading documents, and parsing EPO Boards of Appeal decisions.
"""

from .client import AsyncClient
from .models import OPSResponse

__all__ = ["AsyncClient", "OPSResponse"]

