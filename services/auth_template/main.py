from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from shared.config import db, fb_auth
from firebase_admin import firestore
from dotenv import load_dotenv
import os
import requests
import logging
from models import UserCreate, ChildCreate, RefreshTokenRequest, TemplateModel

load_dotenv() # load .env

app = FastAPI()

security = HTTPBearer()  #  tokens JWT

logger = logging.getLogger(__name__)

# @app.get("/users")
# async def get_users():
#     users_ref = db.collection("users").get()
#     users = [user.to_dict() for user in users_ref]
#     return {"users": users}

""" Users """

# Check authenticated user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = fb_auth.verify_id_token(credentials.credentials)
        logger.info(f"Token decodificado: {decoded_token}")
        user_id = decoded_token['uid']
        role = decoded_token.get('role', 'child')
        main_user_id = decoded_token.get('mainUserId', user_id)  
        return {'uid': user_id, 'role': role, 'mainUserId': main_user_id}
    except:
        Logger.error(f"Erro ao verificar token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token inválido")

# requeire main user  role: 'main'
def require_main_role(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'main':
        raise HTTPException(status_code=403, detail="Apenas main users podem acessar")
    return current_user

# register main user
@app.post("/register-main")
async def register_main_user(user: UserCreate):
    try:
        created_user = fb_auth.create_user(email=user.email, password=user.password)
        # check requirements for register
        fb_auth.set_custom_user_claims(created_user.uid, {'role': 'main', 'mainUserId': created_user.uid})
        
        db.collection('users').document(created_user.uid).set({
            'name': user.name,
            'email': user.email,
            'isMain': True,
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Main user criado", "uid": created_user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# register child user, only main user can crate child users
@app.post("/child-users")
async def register_child_user(child: ChildCreate, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    try:

        created_child = fb_auth.create_user(email=child.email, password=child.password)
        # check requirements for register 
        fb_auth.set_custom_user_claims(created_child.uid, {'role': 'child', 'mainUserId': main_user_id})
      
        db.collection('users').document(main_user_id).collection('child_users').document(created_child.uid).set({
            'name': child.name,
            'email': child.email,
            'mainUserId': main_user_id,
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Child user criado", "uid": created_child.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# list Child Users
@app.get("/child-users")
async def list_child_users(current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    child_users = db.collection('users').document(main_user_id).collection('child_users').stream()
    children = [{'id': doc.id, **doc.to_dict()} for doc in child_users]
    return {"child_users": children}

# edit Child User
@app.put("/child-users/{child_id}")
async def update_child_user(child_id: str, updates: dict, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    child_ref = db.collection('users').document(main_user_id).collection('child_users').document(child_id)
    child_doc = child_ref.get()
    if not child_doc.exists:
        raise HTTPException(status_code=404, detail="Child user não encontrado")
    child_ref.update(updates)
    return {"message": "Child user atualizado"}

@app.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    return {"message": f"Usuário logado: {current_user['role']}", "mainId": current_user.get('mainUserId')}


# to refresh user token

def refresh_user_token(refresh_token: str, web_api_key: str):
    url = f"https://securetoken.googleapis.com/v1/token?key={web_api_key}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Erro ao renovar token: {response.json().get('error', 'Desconhecido')}")
    data = response.json()
    return {
        "id_token": data["id_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data["expires_in"]
    }

@app.post("/refresh-token")
async def refresh_token(request: RefreshTokenRequest):
    try:
        # Carregar a WEB_API_KEY do .env
        web_api_key = os.getenv("WEB_API_KEY")
        if not web_api_key:
            raise HTTPException(status_code=500, detail="WEB_API_KEY não encontrada no .env")
        
        print(f"Renovando token com WEB_API_KEY: {web_api_key[:6]}...")
        new_tokens = refresh_user_token(request.refresh_token, web_api_key)
        return {
            "message": "Token renovado",
            "id_token": new_tokens["id_token"],
            "refresh_token": new_tokens["refresh_token"],
            "expires_in": new_tokens["expires_in"]
        }
    except Exception as e:
        print(f"Erro ao renovar token: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/user-role")
async def get_user_role(current_user: dict = Depends(get_current_user)):
    return {"role": current_user['role'], "mainUserId": current_user['mainUserId']}

""" Template """

# list all templates where user_id == mainUserId
@app.get("/templates")
async def get_templates(current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    templates_ref = db.collection("templates").where("user_id", "==", main_user_id).stream()
    templates = [{"id": doc.id, **doc.to_dict()} for doc in templates_ref]
    # return list with name, holidays, shifts
    return {"templates": templates} 

# Select template and load data
@app.post("/select-template/{template_id}")
async def select_template(template_id: str, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    template_ref = db.collection("templates").document(template_id)
    template = template_ref.get()
    if not template.exists or template.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    return {"template": {"id": template.id, **template.to_dict()}, "message": "Template selecionado"}

# add template, and link to user_id
@app.post("/templates")
async def create_template(template: TemplateModel, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        template_data = template.dict()
        template_data["user_id"] = main_user_id
        template_data["createdAt"] = firestore.SERVER_TIMESTAMP
        doc_ref = db.collection("templates").document()
        doc_ref.set(template_data)
        return {"id": doc_ref.id, "message": "Template criado"}
    except Exception as e:
        logger.error(f"Erro ao criar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Edit template
@app.put("/templates/{template_id}")
async def update_template(template_id: str, template: TemplateModel, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    template_ref = db.collection("templates").document(template_id)
    template_doc = template_ref.get()
    if not template_doc.exists or template_doc.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    try:
        template_data = template.dict(exclude={"id", "user_id"})
        template_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        template_ref.update(template_data)
        return {"id": template_id, "message": "Template atualizado", **template_data}
    except Exception as e:
        logger.error(f"Erro ao atualizar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# delete template
@app.delete("/templates/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    template_ref = db.collection("templates").document(template_id)
    template_doc = template_ref.get()
    if not template_doc.exists or template_doc.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    try:
        template_ref.delete()
        return {"message": "Template deletado"}
    except Exception as e:
        logger.error(f"Erro ao deletar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))