from shared.config import logger
from shared.config import db
from fastapi import HTTPException

def get_user_ref(user_id: str):
    user_ref = db.collection('users').document(user_id)
    if not user_ref.get().exists:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User {user_id} not found")
    return user_ref
