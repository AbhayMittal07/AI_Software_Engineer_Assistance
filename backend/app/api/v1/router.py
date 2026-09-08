"""Aggregated API v1 router."""
from fastapi import APIRouter

from app.api.v1 import auth, chat, diagrams, documentation, reports, repositories, reviews, system, users

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(repositories.router)
api_router.include_router(reviews.router)
api_router.include_router(documentation.router)
api_router.include_router(diagrams.router)
api_router.include_router(reports.router)
api_router.include_router(chat.router)
