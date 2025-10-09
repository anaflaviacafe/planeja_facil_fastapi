# shared/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as fb_auth
import jwt
import requests
from .config import logger

# login auth

security = HTTPBearer()
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        logger.info("Verifying token")
        # decoded_token = fb_auth.verify_id_token(credentials.credentials, check_revoked=True)
        # Explicitly set clock skew to 10 minutes (600 seconds)
        decoded_token = fb_auth.verify_id_token(credentials.credentials, clock_skew_seconds=600, check_revoked=True)
        logger.info(f"Token decoded: {decoded_token}")
        user_id = decoded_token['uid']
        role = decoded_token.get('role', 'child')
        main_user_id = decoded_token.get('mainUserId', user_id)
        return {'uid': user_id, 'role': role, 'mainUserId': main_user_id}
    except fb_auth.InvalidIdTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except fb_auth.ExpiredIdTokenError as e:
        logger.error(f"Expired token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token expired")
    except fb_auth.RevokedIdTokenError as e:
        logger.error(f"Revoked token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token revoked")
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Unexpected error: {str(e)}")

def require_main_role(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'main':
        logger.error(f"Usuário {current_user['uid']} não é main, role: {current_user['role']}")
        raise HTTPException(status_code=403, detail="Apenas main users podem acessar")
    return current_user