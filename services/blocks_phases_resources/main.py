from fastapi import FastAPI, Depends, HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, PhaseUpdateResource
from shared.auth import get_current_user, require_main_role
from shared.config import logger

app = FastAPI()

# Reusable function to validate template existence and ownership
def validate_template(template_id: str, main_user_id: str) -> None:
    """
    Validates that a template exists and belongs to the main user.
    
    Args:
        template_id: The ID of the template to validate.
        main_user_id: The main user ID to check ownership against.
    
    Raises:
        HTTPException: If the template doesn't exist (404) or doesn't belong to the main user (403).
    """
    template_ref = db.collection('templates').document(template_id)
    template_doc = template_ref.get()
    if not template_doc.exists:
        logger.error(f"Template {template_id} not found")
        raise HTTPException(status_code=404, detail="Template not found")
    if template_doc.to_dict().get('user_id') != main_user_id:
        logger.error(f"Template {template_id} does not belong to mainUserId {main_user_id}")
        raise HTTPException(status_code=403, detail="Access denied: Template does not belong to the main user")


# Create a block (main users only)
@app.post("/blocks")
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
            "durationType": duration_types[block.durationType],  # Convert int to string
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection("blocks").add(block_data)
        block_id = doc_ref[1].id
        logger.info(f"Block created: {block_id}")
        return {"message": "Block created", "id": block_id}
    except Exception as e:
        logger.error(f"Error creating block: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List blocks
@app.get("/blocks")
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
      
        blocks_ref = db.collection('blocks').where(
            filter=FieldFilter('mainUserId', '==', main_user_id)
        ).where(
            filter=FieldFilter('templateId', '==', selected_template)  
        )
        
        #blocks = blocks_ref.get()
        #blocks_list = [{"id": block.id, **block.to_dict()} for block in blocks]

        blocks = blocks_ref.get()
        blocks_list = []
        for block in blocks:
            block_data = block.to_dict()
            block_data['id'] = block.id
            blocks_list.append(block_data)
        
        logger.info(f"Blocks found: {len(blocks_list)}")
        return {"blocks": blocks_list}
    except Exception as e:
        logger.error(f"Error listing blocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# update block
@app.put("/blocks/{block_id}")
async def update_block(block_id: str, block: BlockCreate, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']

    # Reference the block document in Firestore
    block_ref = db.collection("blocks").document(block_id)
    block_doc = block_ref.get()

    # Check block exists and belongs to the main user
    if not block_doc.exists or block_doc.to_dict().get("mainUserId") != main_user_id:
        raise HTTPException(status_code=404, detail="Bloco não encontrado ou não pertence ao usuário")
    try:
   
        # id keep the same  
        # block_data = block.dict(exclude={"id", "block_id"})    
        block_data = block.dict(exclude_unset=True)  # Exclude unset fields to avoid overwriting with null, also excluds id
        #logger.info(f"Dados recebidos para atualização: {block.dict()}") 
        block_data["updatedAt"] = firestore.SERVER_TIMESTAMP
             
        # Update block document in Firestore
        block_ref.update(block_data)
       
        return {"id": block_id, "message": "Bloco atualizado", "name": block_data["name"]}
    except Exception as e:
        logger.error(f"Erro ao atualizar bloco: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
       
# delete a block
@app.delete("/blocks/{block_id}")
async def delete_block(block_id: str, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
    try:
        
       # Reference the block document
        block_ref = db.collection("blocks").document(block_id)
        block_doc = block_ref.get()

        if not block_doc.exists:
            logger.error(f"Block {block_id} not found for main user {main_user_id}")
            raise HTTPException(status_code=404, detail="Bloco não encontrado")

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

        return {"message": "Bloco deletado com sucesso"}
    except Exception as e:
        logger.error(f"Error deleting block {block_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao deletar child user: {str(e)}")

# Create a phase inside block route
@app.post("/blocks/{block_id}/phases")
async def create_phase(block_id: str, phase: PhaseCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
       
        # Check if block exists and belongs to mainUserId
        block_ref = db.collection('blocks').document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Block {block_id} not found")
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
@app.get("/blocks/{block_id}/phases")
async def get_phases(block_id: str, current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Fetching phases for block {block_id}, mainUserId: {main_user_id}")
        
        block_ref = db.collection("blocks").document(block_id)
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

            # Fetch resource data for the resources list
            if phase_data.get("resources"):  
                phase_data["resource_details"] = []
                for resource_id in phase_data["resources"]:
                    resource_doc = db.collection("resources").document(resource_id).get()
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

# Create a resource 
@app.post("/resources")
async def create_resource(resource: ResourceCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        user_id = current_user['uid']
        
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
        
        doc_ref = db.collection("resources").add(resource_data)
        resource_id = doc_ref[1].id
       
        logger.info(f"Resource created: {resource_id}")
        return {"message": "Resource created", "id": resource_id}
    except Exception as e:
        logger.error(f"Error creating resource: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List resources (main and child users)
@app.get("/resources")
async def get_resources(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Fetching resources for mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")
        
        # Updated to use FieldFilter to avoid Firestore warning
        resources_ref = db.collection("resources").where(
            filter=FieldFilter("mainUserId", "==", main_user_id)
        ).get()
        resources = []
        for doc in resources_ref:
            resource_data = doc.to_dict()
            resource_data["id"] = doc.id
            resources.append(resource_data)
        
        logger.info(f"Resources returned: {len(resources)} resources")
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Associate resource in phase inside block
@app.post("/blocks/{block_id}/phases/{phase_id}/resources")
async def add_resource_to_phase(block_id: str, phase_id: str, resource: PhaseUpdateResource, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']

        # Verify block exists and belongs to mainUserId
        block_ref = db.collection('blocks').document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Block {block_id} not found")
            raise HTTPException(status_code=404, detail="Block not found")
        if block_doc.to_dict().get('mainUserId') != main_user_id:
            logger.error(f"Block {block_id} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied")

        # Verify phase exists
        phase_ref = block_ref.collection('phases').document(phase_id)
        phase_doc = phase_ref.get()
        if not phase_doc.exists:
            logger.error(f"Phase {phase_id} not found in block {block_id}")
            raise HTTPException(status_code=404, detail="Phase not found")

        # Verify resource exists and belongs to mainUserId
        resource_ref = db.collection('resources').document(resource.resourceId)
        resource_doc = resource_ref.get()
        if not resource_doc.exists:
            logger.error(f"Resource {resource.resourceId} not found")
            raise HTTPException(status_code=404, detail="Resource not found")
        if resource_doc.to_dict().get('mainUserId') != main_user_id:
            logger.error(f"Resource {resource.resourceId} does not belong to mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Access denied")

        # Add resourceId to phase's resources list
        phase_data = phase_doc.to_dict()
        resources = phase_data.get('resources', [])  # List of resourceIds
        if resource.resourceId not in resources:
            resources.append(resource.resourceId)
            phase_ref.update({"resources": resources})
            logger.info(f"Resource {resource.resourceId} associated with phase {phase_id}")
        else:
            logger.info(f"Resource {resource.resourceId} already associated with phase {phase_id}")

        return {"message": f"Resource {resource.resourceId} associated with phase {phase_id}"}
    except Exception as e:
        logger.error(f"Error associating resource with phase: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))