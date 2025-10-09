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




# Run this locally to delete a user and all their data

def delete_user_and_data(user_id: str):
    try:
        # Delete user from Firebase Authentication
        auth.delete_user(user_id)
        print(f"Deleted user {user_id} from Firebase Authentication")

        # Delete Firestore data
        user_ref = db.collection('users').document(user_id)
        if user_ref.get().exists:
            for subcoll in user_ref.collections():
                for doc in subcoll.stream():
                    for subsubcoll in doc.reference.collections():
                        for subdoc in subsubcoll.stream():
                            subdoc.reference.delete()
                    doc.reference.delete()
                print(f"Deleted subcollection {subcoll.id} for user {user_id}")
            user_ref.delete()
            print(f"Deleted user document {user_id}")
    except Exception as e:
        print(f"Error: {str(e)}")

# Run
# delete_user_and_data("id_here")
