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

phases_router = APIRouter()

# Create a phase inside block route
@phases_router.post("/blocks/{block_id}/phases")
async def create_phase(block_id: str, phase: PhaseCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Request create phase, block_id: '{block_id}', user_id: '{main_user_id}'")
       
        # Check if block exists and belongs to mainUserId
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()
        #logger.info(f"block_doc exists: {block_doc.exists}")
        
        if block_doc.exists:
            block_data = block_doc.to_dict()
            logger.info(f"Block data: {block_data}")
        
        if not block_doc.exists:
            logger.error(f"Block '{block_id}' not found")
            raise HTTPException(status_code=404, detail="Block not found")
        if block_doc.to_dict().get('mainUserId') != main_user_id:
            logger.error(f"Block {block_id} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied")            

        phase_data = {
            "name": phase.name,
            "description": phase.description,
            "duration": phase.duration,
            "mainUserId": main_user_id,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = block_ref.collection('phases').add(phase_data)
        phase_id = doc_ref[1].id

        logger.info(f"Phase created: {phase_id}")
        return {"message": "Phase created", "id": phase_id}
    except Exception as e:
        logger.error(f"Error creating phase: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List phases for a block (main and child users)
@phases_router.get("/blocks/{block_id}/phases")
async def get_phases(block_id: str, current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Fetching phases for block {block_id}, mainUserId: {main_user_id}")
        
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()
        
        if not block_doc.exists:
            logger.error(f"Block {block_id} not found")
            raise HTTPException(status_code=404, detail="Block not found")
        if block_doc.to_dict().get("mainUserId") != main_user_id:
            logger.error(f"Block {block_id} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied: Block does not belong to the main user")

        phases_ref = block_ref.collection("phases").get()
        phases = []
        for doc in phases_ref:
            phase_data = doc.to_dict()
            phase_data["id"] = doc.id

            if phase_data.get("resources"):  
                phase_data["resource_details"] = []
                for resource_id in phase_data["resources"]:
                    resource_doc = db.collection('users').document(main_user_id).collection("resources").document(resource_id).get()
                    if resource_doc.exists:
                        resource_data = resource_doc.to_dict()
                        resource_data["id"] = resource_id
                        phase_data["resource_details"].append(resource_data)
            phases.append(phase_data)
        
        logger.info(f"Phases returned: {len(phases)} phases")
        return {"phases": phases}
    except Exception as e:
        logger.error(f"Error listing phases: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    

# Delete a phase from block (main users only)
@phases_router.delete("/blocks/{block_id}/phases/{phase_id}")
async def delete_phase(block_id: str, phase_id: str, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Request delete phase: block_id='{block_id}', phase_id='{phase_id}', user_id='{main_user_id}'")
        
        # Check if block exists and belongs to mainUserId
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()
        
        if not block_doc.exists:
            logger.error(f"Block '{block_id}' not found")
            raise HTTPException(status_code=404, detail="Block not found")
        if block_doc.to_dict().get('mainUserId') != main_user_id:
            logger.error(f"Block {block_id} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if phase exists
        phase_ref = block_ref.collection('phases').document(phase_id)
        phase_doc = phase_ref.get()
        
        if not phase_doc.exists:
            logger.error(f"Phase '{phase_id}' not found in block '{block_id}'")
            raise HTTPException(status_code=404, detail="Phase not found")
        
        # Delete phase
        phase_ref.delete()
        
        logger.info(f"✅ Phase '{phase_id}' deleted from block '{block_id}'")
        return {"message": "Phase deleted successfully", "id": phase_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting phase: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    

# Update phase (main users only)
@phases_router.put("/blocks/{block_id}/phases/{phase_id}")
async def update_phase(
    block_id: str, 
    phase_id: str, 
    phase: PhaseCreate,  
    current_user: dict = Depends(require_main_role)
):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Request update phase: block_id='{block_id}', phase_id='{phase_id}', user_id='{main_user_id}'")
        
        #  Check block
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists or block_doc.to_dict().get('mainUserId') != main_user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check phase exists
        phase_ref = block_ref.collection('phases').document(phase_id)
        phase_doc = phase_ref.get()
        if not phase_doc.exists:
            raise HTTPException(status_code=404, detail="Phase not found")
        
        # Update phase
        phase_update_data = {
            "name": phase.name,
            "description": phase.description,
            "duration": phase.duration,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        phase_ref.update(phase_update_data)
        
        logger.info(f"Phase '{phase_id}' updated in block '{block_id}'")
        return {"message": "Phase updated", "id": phase_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating phase: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

