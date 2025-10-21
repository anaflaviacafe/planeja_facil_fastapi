from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from shared.config import db
import os
from models import*
from shared.auth import get_current_user, require_main_role
from shared.config import logger

resources_type_router = APIRouter()

# create resource type
@resources_type_router.post("/resources-types")
async def add_resource_type(resource_type: ResourceTypeCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        resources_types_ref = db.collection('users').document(main_user_id).collection('resourcesTypes')
        
        # Check if type already exists
        existing_types = resources_types_ref.where('name', '==', resource_type.name).get()
        if existing_types:
            logger.error(f"Resource type '{resource_type.name}' already exists for user {main_user_id}")
            raise HTTPException(status_code=400, detail="Resource type already exists")
        
        # Add new type (not default)
        doc_ref = resources_types_ref.add({
            'name': resource_type.name,
            'isDefault': False,
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        logger.info(f"Added resource type '{resource_type.name}' for user {main_user_id}")
        return {"message": "Resource type added", "id": doc_ref[1].id}
    except Exception as e:
        logger.error(f"Error adding resource type: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
# Delete a resource type
@resources_type_router.delete("/resources-types/{type_id}")
async def delete_resource_type(type_id: str, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        resources_types_ref = db.collection('users').document(main_user_id).collection('resourcesTypes')
        doc_ref = resources_types_ref.document(type_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.error(f"Resource type {type_id} not found for user {main_user_id}")
            raise HTTPException(status_code=404, detail="Resource type not found")
        
        # Prevent deletion of default types
        if doc.to_dict().get('isDefault', False):
            logger.error(f"Attempted to delete default resource type {type_id} for user {main_user_id}")
            raise HTTPException(status_code=403, detail="Cannot delete default resource types")
        
        # Check if type is in use (optional, if you have a resources collection)
        resources_ref = db.collection('users').document(main_user_id).collection('resources')
        resources_using_type = resources_ref.where('typeId', '==', type_id).get()
        if resources_using_type:
            logger.error(f"Resource type {type_id} is in use by resources")
            raise HTTPException(status_code=400, detail="Cannot delete resource type in use")

        doc_ref.delete()
        logger.info(f"Deleted resource type {type_id} for user {main_user_id}")
        return {"message": "Resource type deleted"}
    except Exception as e:
        logger.error(f"Error deleting resource type: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
# get resource types
@resources_type_router.get("/resources-types")
async def get_resource_types(current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        resources_types_ref = db.collection('users').document(main_user_id).collection('resourcesTypes')
        docs = resources_types_ref.stream()
        resource_types = [
            {"id": doc.id, **doc.to_dict()} for doc in docs
        ]
        logger.info(f"Retrieved {len(resource_types)} resource types for user {main_user_id}")
        return resource_types
    except Exception as e:
        logger.error(f"Error retrieving resource types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
