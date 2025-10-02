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
        logger.error(f"Erro ao verificar token: {str(e)}")
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
        # check requirements for register, and define custom claims (role: 'main', mainUserId: <uid>)
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

@app.put("/users/{user_id}")
async def update_main_user(user_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    if current_user['uid'] != user_id or current_user['role'] != 'main':
        raise HTTPException(status_code=403, detail="Apenas o próprio usuário principal pode atualizar seus dados")
    
    logger.info(f"Atualizando usuário principal {user_id} com dados: {updates}")
    
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            logger.error(f"Usuário {user_id} não encontrado")
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        allowed_fields = {'name', 'email', 'password'}
        if not all(key in allowed_fields for key in updates.keys()):
            logger.error(f"Campos inválidos fornecidos: {updates.keys()}")
            raise HTTPException(status_code=400, detail="Campos inválidos fornecidos")

        # Validate non-empty fields
        if 'name' in updates and not updates['name'].strip():
            raise HTTPException(status_code=400, detail="Nome não pode ser vazio")
        if 'email' in updates and not updates['email'].strip():
            raise HTTPException(status_code=400, detail="Email não pode ser vazio")
        if 'password' in updates and len(updates['password']) < 6:
            raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")

        firestore_updates = {}
        if 'name' in updates:
            firestore_updates['name'] = updates['name']
            logger.info(f"Atualizando nome para: {updates['name']}")
        if 'email' in updates:
            firestore_updates['email'] = updates['email']
            logger.info(f"Atualizando email para: {updates['email']} via Firebase Auth")
            fb_auth.update_user(user_id, email=updates['email'])
        if 'password' in updates:
            logger.info(f"Atualizando senha via Firebase Auth")
            fb_auth.update_user(user_id, password=updates['password'])

        if firestore_updates:
            firestore_updates['updatedAt'] = firestore.SERVER_TIMESTAMP
            user_ref.update(firestore_updates)
            logger.info(f"Usuário principal {user_id} atualizado com sucesso")

        # Revoke refresh tokens if sensitive change
        if 'password' in updates or 'email' in updates:
            logger.info(f"Revogando tokens de refresh para {user_id}")
            fb_auth.revoke_refresh_tokens(user_id)

        return {"message": "Usuário principal atualizado"}
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário principal {user_id}: {str(e)}")
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


@app.delete("/child-users/{child_id}")
async def delete_child_user(child_id: str, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    try:
        # Reference to the child user in Firestore
        child_ref = db.collection('users').document(main_user_id).collection('child_users').document(child_id)
        child_doc = child_ref.get()

        # Check if the child user exists
        if not child_doc.exists:
            logger.error(f"Child user {child_id} not found for main user {main_user_id}")
            raise HTTPException(status_code=404, detail="Child user não encontrado")

        # Delete from Firestore
        child_ref.delete()
        logger.info(f"Child user {child_id} deleted from Firestore for main user {main_user_id}")

        # Delete from Firebase Authentication
        try:
            fb_auth.delete_user(child_id)
            logger.info(f"Child user {child_id} deleted from Firebase Authentication")
        except Exception as e:
            logger.warning(f"Failed to delete child user {child_id} from Firebase Authentication: {str(e)}")
     
        return {"message": "Child user deletado com sucesso"}
    except Exception as e:
        logger.error(f"Error deleting child user {child_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao deletar child user: {str(e)}")
    
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

# @app.get("/user-role")
# async def get_user_role(current_user: dict = Depends(get_current_user)):
#     return {"role": current_user['role'], "mainUserId": current_user['mainUserId']}

@app.get("/user-role")
async def get_user_role(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user['uid']
        role = current_user['role']
        main_user_id = current_user['mainUserId']
        logger.info(f"Obtendo papel para usuário {user_id} (role: {role}, mainUserId: {main_user_id})")

        # Fetch user data from Firestore
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.error(f"Usuário {user_id} não encontrado no Firestore")
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        user_data = user_doc.to_dict()
        response = {
            "role": role,
            "mainUserId": main_user_id,
            "name": user_data.get('name', '')
        }
        logger.info(f"Resposta do user-role: {response}")
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao obter papel do usuário {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao obter papel do usuário: {str(e)}")
    
""" Template """

# List all templates for the main user associated with the current user (main or child)
@app.get("/templates")
async def get_templates(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Buscando templates para mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")
        templates_ref = db.collection("templates").where("user_id", "==", main_user_id).get()
        templates = []
        for doc in templates_ref:
            logger.info(f"Documento encontrado: {doc.id}")
            template_data = doc.to_dict()
            week_start = template_data.get("weekStart", 1)  # Default to Monday (1)
            week_end = template_data.get("weekEnd", 5)      # Default to Friday (5)
            template_data["weekStart"] = (week_start - 1) % 7  # Convert to 0-based
            template_data["weekEnd"] = (week_end - 1) % 7      # Convert to 0-based
            template_data['id'] = doc.id
            templates.append(template_data)
        logger.info(f"Templates retornados: {len(templates)} templates")
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Erro ao listar templates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Select a specific template by ID
@app.post("/select-template/{template_id}")
async def select_template(template_id: str, current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Selecionando template {template_id} para mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")
        
        # Fetch the template from Firestore
        template_ref = db.collection("templates").document(template_id)
        template_doc = template_ref.get()

        if not template_doc.exists:
            logger.error(f"Template {template_id} não encontrado")
            raise HTTPException(status_code=404, detail="Template não encontrado")

        template_data = template_doc.to_dict()
        
        # Verify that the template belongs to the mainUserId
        if template_data.get("user_id") != main_user_id:
            logger.error(f"Template {template_id} não pertence ao mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Acesso negado: Template não pertence ao usuário principal")

        # Process weekStart and weekEnd (consistent with /templates)
        week_start = template_data.get("weekStart", 1)  # Default to Monday (1)
        week_end = template_data.get("weekEnd", 5)      # Default to Friday (5)
        template_data["weekStart"] = (week_start - 1) % 7  # Convert to 0-based (Sunday = 0)
        template_data["weekEnd"] = (week_end - 1) % 7      # Convert to 0-based
        template_data["id"] = template_doc.id

        logger.info(f"Template selecionado: {template_data}")
        return {"template": template_data}
    except Exception as e:
        logger.error(f"Erro ao selecionar template {template_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# add template, and link to user_id
@app.post("/templates")
async def create_template(template: TemplateModel, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        template_data = template.dict()
        template_data["user_id"] = main_user_id
        template_data["createdAt"] = firestore.SERVER_TIMESTAMP
        template_data["weekStart"] = template.weekStart  
        template_data["weekEnd"] = template.weekEnd   
        doc_ref = db.collection("templates").document()
        doc_ref.set(template_data)
        return {"id": doc_ref.id, "message": "Template criado"}
    except Exception as e:
        logger.error(f"Erro ao criar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Update template
@app.put("/templates/{template_id}")
async def update_template(template_id: str, template: TemplateModel, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    template_ref = db.collection("templates").document(template_id)
    template_doc = template_ref.get()
    if not template_doc.exists or template_doc.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    try:
        template_data = template.dict(exclude={"id", "user_id"}) # exclude in Config
        logger.info(f"Dados recebidos para atualização: {template.dict()}")
        template_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        template_data["weekStart"] = template.weekStart 
        template_data["weekEnd"] = template.weekEnd    
        template_ref.update(template_data)
        return {"id": template_id, "message": "Template atualizado", "name": template_data["name"]}
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