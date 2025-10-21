from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, PhaseUpdateResource
from shared.auth import get_current_user, require_main_role
from shared.config import logger
from utils import validate_template

router = APIRouter()