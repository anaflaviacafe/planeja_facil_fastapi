from fastapi import FastAPI, Depends, HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, PhaseUpdateResource
from shared.auth import get_current_user, require_main_role
from shared.config import logger
from utils import validate_template

from blocks import blocks_router
from phases import phases_router
from resources import resources_router
from ops import op_router

app = FastAPI()

app.include_router(blocks_router)
app.include_router(phases_router)
app.include_router(resources_router)
app.include_router(op_router)

    