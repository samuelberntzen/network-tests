from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn


from app.routes.api import router as api_router

app = FastAPI()

# Cors middleware
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
