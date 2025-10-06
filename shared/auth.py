# shared/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as fb_auth
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = fb_auth.verify_id_token(credentials.credentials)
        logger.info(f"Token decodificado: {decoded_token}")
        user_id = decoded_token['uid']
        role = decoded_token.get('role', 'child')
        main_user_id = decoded_token.get('mainUserId', user_id)
        return {'uid': user_id, 'role': role, 'mainUserId': main_user_id}
    except fb_auth.InvalidIdTokenError:
        logger.error("Token inválido fornecido")
        raise HTTPException(status_code=401, detail="Token inválido")
    except fb_auth.ExpiredIdTokenError:
        logger.error("Token expirado fornecido")
        raise HTTPException(status_code=401, detail="Token expirado")
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar token: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao verificar token")

def require_main_role(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'main':
        logger.error(f"Usuário {current_user['uid']} não é main, role: {current_user['role']}")
        raise HTTPException(status_code=403, detail="Apenas main users podem acessar")
    return current_user