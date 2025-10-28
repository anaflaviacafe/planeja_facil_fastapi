from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, OpModel
from shared.auth import get_current_user, require_main_role
from shared.config import logger
from typing import List
from utils import validate_template

op_router = APIRouter()

# Create a op (main users only)
@op_router.post("/op")
async def create_op(op: OpModel, current_user: dict = Depends(require_main_role)):
    try:
        #print("Received data from frontend:", op.model_dump())

        main_user_id = current_user['mainUserId']
        user_id = current_user['uid'] # current user logged

        # Validate templateId
        if not op.templateId:
            logger.error(f"User {user_id} did not provide templateId")
            raise HTTPException(status_code=400, detail="No templateId provided")

        # Validate template existence and ownership
        validate_template(op.templateId, main_user_id)

        op_data = op.model_dump(by_alias=True, exclude_unset=True)
              
        # op_data = {
        #     'id': op.id,
        #     'mainUserId': op.user_id,
        #     'templateId': op.templateId,
        #     'description': op.description,
        #     'code': op.code,
        #     'dateCreated': op.dateCreated.isoformat() if op.dateCreated else None,
        #     'dateLimit': op.dateLimit.isoformat() if op.dateLimit else None,
        #     'dateStart': op.dateStart.isoformat() if op.dateStart else None,
        #     'dateEnd': op.dateEnd.isoformat() if op.dateEnd else None,
        #     'status': op.status.value,
        #     'priority': op.priority.value,
        #     'estimatedDuration': op.estimatedDuration,
        #     'quantity': op.quantity,
        #     'progressPrc': op.progressPrc,
        #     'inProducing': op.inProducing,
        #     'active': op.active,
        #     'customColumn': op.customColumn,
        #     'operatorName': op.operatorName,
        #     'block': op.block.to_dict() if op.block else None,
        #     'phase': op.phase.to_dict() if op.phase else None,
        #     'resource': op.resource.to_dict() if op.resource else None,
        #     "createdAt": firestore.SERVER_TIMESTAMP
        # }

        op_data["mainUserId"] = main_user_id 
        op_data["createdAt"] = firestore.SERVER_TIMESTAMP
        
        op_ref = db.collection("users").document(main_user_id).collection("ops")
        doc_ref = op_ref.add(op_data)

        op_id = doc_ref[1].id
        logger.info(f"Op created: {op_id}")
        return {"message": "Op created", "id": op_id}
    except ValueError as ve:
        logger.error(f"Value error creating op: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(ve)}")
    except Exception as e:
        logger.error(f"Unexpected error creating op: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
# List ops
@op_router.get("/ops")
async def list_ops(current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        user_id = current_user['uid']

        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.error(f"User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        selected_template = user_doc.to_dict().get('selectedTemplate')
        
        if not selected_template:
            logger.info(f"User {user_id} has no selected template")
            return {"ops": []}

        logger.info(f"Listing ops for mainUserId: {main_user_id}, template: {selected_template}")

        op_ref = db.collection("users").document(main_user_id).collection("ops").where(
            filter=FieldFilter('mainUserId', '==', main_user_id)
        ).where(
            filter=FieldFilter('templateId', '==', selected_template)
        )

        ops = op_ref.get()
        op_list = []
        for op in ops:
            op_data = op.to_dict()
            op_data['id'] = op.id
            #logger.info(f"Op {op.id} block: {op_data.get('block')}")  #
            op_list.append(op_data)
            logger.debug(f"Op found: {op_data}")  
                
        logger.info(f"Ops found: {len(op_list)}")
        return {"ops": op_list}
    except Exception as e:
        logger.error(f"Error listing ops: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get one op
# @op_router.get("/op/{op_id}", response_model=OpModel)
# async def get_op(op_id: str, current_user: dict = Depends(require_main_role)):
#     try:
#         main_user_id = current_user['mainUserId']
        
#         op_ref = db.collection("users").document(main_user_id).collection("ops").document(op_id)
#         op_doc = op_ref.get()
        
#         if not op_doc.exists:
#             logger.error(f"Op {op_id} not found for user {main_user_id}")
#             raise HTTPException(status_code=404, detail="Op not found")
        
#         op_data = op_doc.to_dict()
#         op_data['id'] = op_id
#         logger.info(f"Retrieved op {op_id} for user {main_user_id}")
#         return OpModel(**op_data)
#     except Exception as e:
#         logger.error(f"Error retrieving op {op_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Delete op
@op_router.delete("/op/{op_id}")
async def delete_op(op_id: str, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        
        op_ref = db.collection("users").document(main_user_id).collection("ops").document(op_id)
        op_doc = op_ref.get()
        
        if not op_doc.exists:
            logger.error(f"Op {op_id} not found for user {main_user_id}")
            raise HTTPException(status_code=404, detail="Op not found")
        
        op_ref.delete()
        logger.info(f"Op {op_id} deleted for user {main_user_id}")
        return {"message": "Op deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting op {op_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# update op
@op_router.put("/ops/{op_id}")
async def update_op(op_id: str, op: OpModel, current_user: dict = Depends(require_main_role)):
    main_user_id = current_user['mainUserId']
        
    op_ref = db.collection("users").document(main_user_id).collection("ops").document(op_id)
    op_doc = op_ref.get()
    
    if not op_doc.exists:
        logger.error(f"Op {op_id} not found for user {main_user_id}")
        raise HTTPException(status_code=404, detail="Op not found")

    try:   
        # Exclude unset fields to avoid overwriting with null, also excluds id
        op_data = op.dict(exclude_unset=True, exclude={"id", "op_id"})        
        # logger.info(f"Updating op {op_id} with fields: {list(op_data.keys())}")
        # logger.info(f"op data received: {op.dict()}") 
        op_data["updatedAt"] = firestore.SERVER_TIMESTAMP
             
        # Update op document in Firestore
        op_ref.update(op_data)
       
        return {"id": op_id, "message": "Op updated", "code": op_data["code"]}
    except Exception as e:
        logger.error(f"Error on update op: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))