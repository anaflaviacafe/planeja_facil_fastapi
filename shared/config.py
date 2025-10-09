import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging

# Firebase Initialization
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)
#client for firestore
db = firestore.client()
# Firebase Authentication
fb_auth = auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
