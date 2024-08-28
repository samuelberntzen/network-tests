from fastapi import APIRouter
from app.endpoints import pathfinding

router = APIRouter()
router.include_router(pathfinding.router)
