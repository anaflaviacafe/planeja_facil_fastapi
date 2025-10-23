from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, OpModel
from shared.auth import get_current_user, require_main_role
from shared.config import logger
from utils import validate_template

op_router = APIRouter()

# Create a op (main users only)
@op_router.post("/op")
async def create_op(op: OpModel, current_user: dict = Depends(require_main_role)):
    try:
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