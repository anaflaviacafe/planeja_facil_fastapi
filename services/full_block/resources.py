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

resources_router = APIRouter()
    
# create resource
@resources_router.post("/resources")
async def create_resource(resource: ResourceCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        user_id = current_user['uid'] # current user logged

        # Validate templateId
        if not resource.templateId:
            logger.error(f"User {user_id} did not provide templateId")
            raise HTTPException(status_code=400, detail="No templateId provided")

        # Validate template existence and ownership
        validate_template(resource.templateId, main_user_id)

        resource_data = {
            "name": resource.name,
            "description": resource.description,
            "code": resource.code,
            "type": resource.type,
            "templateId": resource.templateId,
            "mainUserId": main_user_id,
            "active": resource.active,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        resources_ref = db.collection("users").document(main_user_id).collection("resources")
        doc_ref = resources_ref.add(resource_data)           
        resource_id = doc_ref[1].id
        
        logger.info(f"Resource created: {resource_data}, ID: {resource_id}")
        return {"message": "Resource created", "id": resource_id}
    except Exception as e:
        logger.error(f"Error creating resource: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    

# List resources (main and child users)
@resources_router.get("/resources")
async def get_resources(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        #logger.info(f"Fetching resources for mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")
        
        # firebase doc inside users
        user_ref = db.collection('users').document(current_user['uid'])                
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.error(f"User {current_user['uid']} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        selected_template = user_doc.to_dict().get('selectedTemplate')
        
        if not selected_template:
            return {"resources": []}

        #logger.info(f"Fetching resources for mainUserId: {main_user_id}, template: {selected_template}")
        
        resources_ref = db.collection("users").document(main_user_id).collection("resources").where(
            filter=FieldFilter('templateId', '==', selected_template)  
        ).get() 
        
        resources = []
        for doc in resources_ref: 
            resource_data = doc.to_dict()
            resource_data["id"] = doc.id
            resources.append(resource_data)
        
        logger.info(f"Resources: {len(resources)}")
        return {"resources": resources}
    
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    

@resources_router.put("/resources/{resource_id}")
async def update_resource(resource_id: str,  resource: ResourceCreate,  current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        
        resources_ref = db.collection("users").document(main_user_id).collection("resources")
        doc_ref = resources_ref.document(resource_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.error(f"Resource {resource_id} not found")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        update_data = {}
        if resource.name is not None:
            update_data["name"] = resource.name
        if resource.description is not None:
            update_data["description"] = resource.description
        if resource.code is not None:
            update_data["code"] = resource.code
        if resource.type is not None:
            update_data["type"] = resource.type
        if resource.active is not None:
            update_data["active"] = resource.active
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        doc_ref.update(update_data)
        
        logger.info(f"Resource {resource_id} updated: {update_data}")
        return {"message": "Resource updated", "id": resource_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resource: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@resources_router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: str, 
    current_user: dict = Depends(require_main_role)
):
    try:
        main_user_id = current_user['mainUserId']
        
        resources_ref = db.collection("users").document(main_user_id).collection("resources")
        doc_ref = resources_ref.document(resource_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.error(f"Resource {resource_id} not found")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        doc_ref.delete()
        
        logger.info(f"Resource {resource_id} deleted successfully")
        return {"message": "Resource deleted", "id": resource_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resource: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Assign resource to phase (main users only)
@resources_router.post("/blocks/{block_id}/phases/{phase_id}/assign-resource")
async def assign_resource_to_phase(
    block_id: str,
    phase_id: str,
    resource_id: str,
    current_user: dict = Depends(require_main_role)
):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Assign resource '{resource_id}' to phase '{phase_id}' in block '{block_id}' for user '{main_user_id}'")
        
        # Validate block
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Block {block_id} not found for user {main_user_id}")
            raise HTTPException(status_code=404, detail="Block not found")
        if block_doc.to_dict().get('mainUserId') != main_user_id:
            logger.error(f"Access denied: Block {block_id} does not belong to user {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate phase
        phase_ref = block_ref.collection('phases').document(phase_id)
        phase_doc = phase_ref.get()
        if not phase_doc.exists:
            logger.error(f"Phase {phase_id} not found in block {block_id}")
            raise HTTPException(status_code=404, detail="Phase not found")
        
        # Validate resource
        resource_ref = db.collection('users').document(main_user_id).collection("resources").document(resource_id)
        resource_doc = resource_ref.get()
        if not resource_doc.exists:
            logger.error(f"Resource {resource_id} not found for user {main_user_id}")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Update phase
        phase_ref.update({
            'resources': [resource_id],  
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Phase '{phase_id}' resource ASSIGNED to '{resource_id}' (overwritten)")
        return {"message": "Resource assigned", "phase_id": phase_id, "resource_id": resource_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning resource: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))