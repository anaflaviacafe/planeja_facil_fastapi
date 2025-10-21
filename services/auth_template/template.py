from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from shared.config import db
import os
from models import*
from shared.auth import get_current_user, require_main_role
from shared.config import logger
from utils import get_user_ref

template_router = APIRouter()

# list templates for main user 
@template_router.get("/templates")
async def get_templates(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']

        logger.info(f"Looking for templates for mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")

        #templates_ref = db.collection("templates").where("user_id", "==", main_user_id).get()
        templates_ref = db.collection('users').document(main_user_id).collection("templates").get()
        templates = []

        for doc in templates_ref:         
            template_data = doc.to_dict()
            template_data["id"] = doc.id          
            #logger.info(f"[list]Template: {template_data}") 
            templates.append(template_data)

        logger.info(f"Return {len(templates)} templates")

        return {"templates": templates}
    except Exception as e:
        logger.error(f"Error on templates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@template_router.post("/select-template/{template_id}")
async def select_template(template_id: str, current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        user_id = current_user['uid']

        logger.info(f"Selecting template {template_id} for mainUserId: {main_user_id} (user: {user_id}, role: {current_user['role']})")
        
        user_ref = get_user_ref(main_user_id)
        
        # Fetch the template from Firestore
        # template_ref = db.collection("templates").document(template_id)        
        logger.info(f"Fetching template {template_id} from users/{main_user_id}/templates") # now /users/{main_user_id}/templates
        template_ref = user_ref.collection('templates').document(template_id)
        template_doc = template_ref.get()
        if not template_doc.exists:
            logger.error(f"Template {template_id} not found")
            raise HTTPException(status_code=404, detail="Template not found")

        template_data = template_doc.to_dict()
        if template_data.get("user_id") != main_user_id:
            logger.error(f"Template {template_id} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied: Template does not belong to the main user")

        template_data["id"] = template_id
        
        # Update user's selectedTemplate in Firestore
        user_ref = db.collection('users').document(main_user_id)
        user_ref.update({"selectedTemplate": template_id})
        #logger.info(f"Updated selectedTemplate to {template_id} for user {main_user_id}")

        logger.info(f"Template selected: {template_data}")
        return {"template": template_data}       
    except Exception as e:
        logger.error(f"Error selecting template {template_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# create template
@template_router.post("/templates")
async def create_template(template: TemplateModel, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Creating template for mainUserId: {main_user_id}")

        user_ref = get_user_ref(main_user_id)
            
        template_data = template.dict(exclude={"id", "user_id"})
        #logger.info(f"Template data received: {template_data}") 

        # # link template to main_user_id, create new table not inside main user document
        template_data["user_id"] = main_user_id
        template_data["createdAt"] = firestore.SERVER_TIMESTAMP

        # # Create a new document 'templates' collection
        # doc_ref = db.collection("templates").document()
        # doc_ref.set(template_data)

        # create template inside main user document 
        template_ref = user_ref.collection('templates')
        _, doc_ref = template_ref.add(template_data) 

        return {"id": doc_ref.id, "message": "Template criado"}

    except Exception as e:
        logger.error(f"Erro ao criar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# update template
@template_router.put("/templates/{template_id}")
async def update_template(template_id: str, template: TemplateModel, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
     
    # Reference the template document in Firestore
    # template_ref = db.collection("templates").document(template_id)
    user_ref = get_user_ref(main_user_id)
    template_ref = user_ref.collection('templates').document(template_id)
    template_doc = template_ref.get()

    # Check if the template exists and belongs to the main user
    if not template_doc.exists or template_doc.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    try:
  
        template_data = template.dict(exclude={"id", "user_id"})            
        #logger.info(f"Data received for updating: {template_data}") 
 
        template_data["updatedAt"] = firestore.SERVER_TIMESTAMP       
      
        # Update the template document in Firestore
        template_ref.update(template_data)
       
        return {"id": template_id, "message": "Template atualizado", "name": template_data["name"]}
    except Exception as e:
        logger.error(f"Erro ao atualizar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# delete template
@template_router.delete("/templates/{template_id}")
async def delete_template(template_id: str, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']

    user_ref = get_user_ref(main_user_id)
   
    # template_ref = db.collection("templates").document(template_id)
    template_ref = user_ref.collection("templates").document(template_id)
    template_doc = template_ref.get()
   
   # Check if the template exists and belongs to the main user
    if not template_doc.exists or template_doc.to_dict().get("user_id") != main_user_id:
        raise HTTPException(status_code=404, detail="Template não encontrado ou não pertence ao usuário")
    try:
        # Delete the template document from Firestore
        template_ref.delete()
        return {"message": "Template deletado"}
    except Exception as e:
        logger.error(f"Erro ao deletar template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))