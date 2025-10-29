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

blocks_router = APIRouter()

# Create a block (main users only)
@blocks_router.post("/blocks")
async def create_block(block: BlockCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        user_id = current_user['uid'] # current user logged

        # Validate templateId
        if not block.templateId:
            logger.error(f"User {user_id} did not provide templateId")
            raise HTTPException(status_code=400, detail="No templateId provided")

        # Validate template existence and ownership
        validate_template(block.templateId, main_user_id)

        # Map durationType to string (optional, depending on your needs)
        duration_types = {0: "min", 1: "hours", 2: "days"}
        if block.durationType not in duration_types:
            logger.error(f"Invalid durationType: {block.durationType}")
            raise HTTPException(status_code=400, detail="Invalid duration type")

        block_data = {
            "name": block.name,
            "description": block.description,
            "mainUserId": main_user_id,
            "templateId": block.templateId,
            "durationType": int(block.durationType),
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        #doc_ref = db.collection("blocks").add(block_data)

        block_ref = db.collection("users").document(main_user_id).collection("blocks")
        doc_ref = block_ref.add(block_data)

        block_id = doc_ref[1].id
        logger.info(f"Block created: {block_id}")
        return {"message": "Block created", "id": block_id}
    except Exception as e:
        logger.error(f"Error creating block: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
# list full block
@blocks_router.get("/blocks/full")
async def get_blocks_full(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        blocks_ref = db.collection('users').document(main_user_id).collection("blocks").get()
        blocks = []
        
        for block_doc in blocks_ref:
            block_data = block_doc.to_dict()
            block_data["id"] = block_doc.id
            
            # all phases + resources
            phases_ref = block_doc.reference.collection("phases").get()
            phases = []
            for phase_doc in phases_ref:
                phase_data = phase_doc.to_dict()
                phase_data["id"] = phase_doc.id
                
                if phase_data.get("resources") and len(phase_data["resources"]) > 0:
                    resource_id = phase_data["resources"][0]  
                    resource_doc = db.collection('users').document(main_user_id).collection("resources").document(resource_id).get()
                    if resource_doc.exists:
                        resource_data = resource_doc.to_dict()
                        resource_data["id"] = resource_id
                        phase_data["resource"] = resource_data 
                
                phases.append(phase_data)
            
            block_data["phases"] = phases
            blocks.append(block_data)
        
        return {"blocks": blocks}
    except Exception as e:
        logger.error(f"Error listing full blocks: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
# List blocks
@blocks_router.get("/blocks")
async def get_blocks(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']

        user_ref = db.collection('users').document(current_user['uid'])                
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.error(f"User {current_user['uid']} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        selected_template = user_doc.to_dict().get('selectedTemplate')
        
        if not selected_template:
            logger.info(f"User {current_user['uid']} has no selected template")
            return {"blocks": []}

        logger.info(f"Listing blocks for mainUserId: {main_user_id}, template: {selected_template}")
      
        # blocks_ref = db.collection('blocks').where(
        #     filter=FieldFilter('mainUserId', '==', main_user_id)
        # ).where(
        #     filter=FieldFilter('templateId', '==', selected_template)  
        # )
        # blocks inside users      
        blocks_ref = db.collection('users').document(main_user_id).collection("blocks").where(
            filter=FieldFilter('mainUserId', '==', main_user_id)
        ).where(
            filter=FieldFilter('templateId', '==', selected_template)  
        )

        #blocks = [doc.to_dict() | {"id": doc.id} for doc in blocks_ref]
        #or
        blocks = blocks_ref.get()
        blocks_list = []
        for block in blocks:
            block_data = block.to_dict()
            block_data['id'] = block.id
            blocks_list.append(block_data)
            #logger.info(f"Blocks {block_data}") 
        
        logger.info(f"Blocks found: {len(blocks_list)}")
        return {"blocks": blocks_list}
    except Exception as e:
        logger.error(f"Error listing blocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# update block
@blocks_router.put("/blocks/{block_id}")
async def update_block(block_id: str, block: BlockCreate, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']

    # Reference the block document in Firestore
    #block_ref = db.collection("blocks").document(block_id)
    block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
    block_doc = block_ref.get()

    # Check block exists and belongs to the main user
    if not block_doc.exists or block_doc.to_dict().get("mainUserId") != main_user_id:
        raise HTTPException(status_code=404, detail="Bloco não encontrado ou não pertence ao usuário")
    try:
   
        # id keep the same  
        block_data = block.dict(exclude={"id", "block_id"})    
        block_data["durationType"] = int(block.durationType)
        # block_data = block.dict(exclude_unset=True)  # Exclude unset fields to avoid overwriting with null, also excluds id
        logger.info(f"block data to update: {block.dict()}") 
        block_data["updatedAt"] = firestore.SERVER_TIMESTAMP
             
        # Update block document in Firestore
        block_ref.update(block_data)
       
        return {"id": block_id, "message": "Bloco atualizado", "name": block_data["name"]}
    except Exception as e:
        logger.error(f"Error on update block: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
       
# delete a block
@blocks_router.delete("/blocks/{block_id}")
async def delete_block(block_id: str, current_user: dict = Depends(require_main_role)):
    try:        
        main_user_id = current_user['mainUserId']

        # Reference the block document
        # block_ref = db.collection("blocks").document(block_id)
        block_ref = db.collection('users').document(main_user_id).collection("blocks").document(block_id)
        block_doc = block_ref.get()

        if not block_doc.exists:
            logger.error(f"Block {block_id} not found for main user {main_user_id}")
            raise HTTPException(status_code=404, detail="Block not found")

        # get block data
        block = block_doc.to_dict()

        # Validate templateId
        if not block.get("templateId"):
            logger.error(f"No templateId found for block {block_id}")
            raise HTTPException(status_code=400, detail="No templateId found")

        # Validate template existence and ownership
        validate_template(block["templateId"], main_user_id)

        # Firebase batch (lote) operation to delete a block and its associate phases 
        batch = db.batch()
        batch.delete(block_ref)

        # Delete associated phases (top-level collection)
        phases_query = db.collection("phases").where("blockId", "==", block_id)
        phases_docs = phases_query.get()
        for phase_doc in phases_docs:
            batch.delete(phase_doc.reference)

        # Commit batch (deletes block and phases, preserves resources)
        batch.commit()
        logger.info(f"Block {block_id} and associated phases deleted for main user {main_user_id}")

        ## or sync commit
        # Run synchronous commit in a separate thread
        # loop = asyncio.get_event_loop()
        # with ThreadPoolExecutor() as pool:
        #     await loop.run_in_executor(pool, batch.commit)

        return {"message": "Block deleted"}
    except Exception as e:
        logger.error(f"Error deleting block {block_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao deletar child user: {str(e)}")