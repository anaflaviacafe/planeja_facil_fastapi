import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)

#client for firestore
db = firestore.client()

# Firebase Authentication
fb_auth = auth

# Optional: If you need Realtime Database URL
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "https://<project-id>.firebaseio.com")

