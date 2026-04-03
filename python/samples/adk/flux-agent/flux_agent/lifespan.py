"""Lifespan management for Flux agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the Flux agent."""
    logger.info("Starting Flux GitOps agent...")
    yield
    logger.info("Shutting down Flux GitOps agent...")
