from fastapi import FastAPI, Depends, HTTPException, status
from firebase_admin import firestore
from shared.config import db
from models import BlockCreate, PhaseCreate, ResourceCreate, PhaseUpdateResource
from shared.auth import get_current_user, require_main_role
import logging

app = FastAPI()

logger = logging.getLogger(__name__)


# Create a block (main users only)
@app.post("/blocks")
async def create_block(block: BlockCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        user_ref = db.collection('users').document(current_user['uid'])

        user_doc = user_ref.get()
        if not user_doc.exists:
            logger.error(f"Usuário {current_user['uid']} não encontrado")
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        selected_template = user_doc.to_dict().get('selectedTemplate')
        if not selected_template:
            logger.error(f"Usuário {current_user['uid']} não tem template selecionado")
            raise HTTPException(status_code=400, detail="Nenhum template selecionado")

        block_data = {
            "name": block.name,
            "description": block.description,
            "mainUserId": main_user_id,
            "templateName": selected_template,
            "durationType": "hours",
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection("blocks").add(block_data)
        block_id = doc_ref[1].id
        logger.info(f"Bloco criado: {block_id}")
        return {"message": "Bloco criado", "id": block_id}
    except Exception as e:
        logger.error(f"Erro ao criar bloco: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List blocks (main and child users)
@app.get("/blocks")
async def get_blocks(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        user_ref = db.collection('users').document(current_user['uid'])
        
        user_doc = user_ref.get()
        if not user_doc.exists:
            logger.error(f"Usuário {current_user['uid']} não encontrado")
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        selected_template = user_doc.to_dict().get('selectedTemplate')
        if not selected_template:
            logger.info(f"Usuário {current_user['uid']} não tem template selecionado")
            return {"blocks": []}

        logger.info(f"Listando blocos para mainUserId: {main_user_id}, template: {selected_template}")
        blocks_ref = db.collection('blocks').where('mainUserId', '==', main_user_id).where('templateName', '==', selected_template)
        blocks = blocks_ref.get()
        blocks_list = [{"id": block.id, **block.to_dict()} for block in blocks]
        logger.info(f"Blocos encontrados: {len(blocks_list)}")
        return {"blocks": blocks_list}
    except Exception as e:
        logger.error(f"Erro ao listar blocos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Create a phase (main users only)
@app.post("/blocks/{block_id}/phases")
async def create_phase(block_id: str, phase: PhaseCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Criando fase para bloco {block_id}, mainUserId: {main_user_id}, phase: {phase}")
        
        block_ref = db.collection("blocks").document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Bloco {block_id} não encontrado")
            raise HTTPException(status_code=404, detail="Bloco não encontrado")
        if block_doc.to_dict().get("mainUserId") != main_user_id:
            logger.error(f"Bloco {block_id} não pertence ao mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Acesso negado: Bloco não pertence ao usuário principal")

        phase_data = {
            "name": phase.name,
            "description": phase.description,
            "duration": phase.duration,
            "mainUserId": main_user_id,
            "templateName": phase.templateName,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        phase_ref = block_ref.collection("phases").add(phase_data)
        phase_id = phase_ref[1].id
        logger.info(f"Fase criada: {phase_id} no bloco {block_id}")
        return {"message": "Fase criada", "id": phase_id}
    except Exception as e:
        logger.error(f"Erro ao criar fase: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List phases for a block (main and child users)
@app.get("/blocks/{block_id}/phases")
async def get_phases(block_id: str, current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Buscando fases para bloco {block_id}, mainUserId: {main_user_id}")
        
        block_ref = db.collection("blocks").document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Bloco {block_id} não encontrado")
            raise HTTPException(status_code=404, detail="Bloco não encontrado")
        if block_doc.to_dict().get("mainUserId") != main_user_id:
            logger.error(f"Bloco {block_id} não pertence ao mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Acesso negado: Bloco não pertence ao usuário principal")

        phases_ref = block_ref.collection("phases").get()
        phases = []
        for doc in phases_ref:
            phase_data = doc.to_dict()
            phase_data["id"] = doc.id
            # Optionally fetch resource data if resourceId exists
            if phase_data.get("resourceId"):
                resource_doc = db.collection("resources").document(phase_data["resourceId"]).get()
                if resource_doc.exists:
                    phase_data["resource"] = resource_doc.to_dict()
            phases.append(phase_data)
        
        logger.info(f"Fases retornadas: {len(phases)} fases")
        return {"phases": phases}
    except Exception as e:
        logger.error(f"Erro ao listar fases: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Create a resource (main users only)
@app.post("/resources")
async def create_resource(resource: ResourceCreate, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Criando recurso para mainUserId: {main_user_id}, resource: {resource}")
        
        resource_data = {
            "name": resource.name,
            "description": resource.description,
            "code": resource.code,
            "type": resource.type,
            "mainUserId": main_user_id,
            "templateName": resource.templateName,
            "active": resource.active,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection("resources").add(resource_data)
        resource_id = doc_ref[1].id
        logger.info(f"Recurso criado: {resource_id}")
        return {"message": "Recurso criado", "id": resource_id}
    except Exception as e:
        logger.error(f"Erro ao criar recurso: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# List resources (main and child users)
@app.get("/resources")
async def get_resources(current_user: dict = Depends(get_current_user)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Buscando recursos para mainUserId: {main_user_id} (user: {current_user['uid']}, role: {current_user['role']})")
        
        resources_ref = db.collection("resources").where("mainUserId", "==", main_user_id).get()
        resources = []
        for doc in resources_ref:
            resource_data = doc.to_dict()
            resource_data["id"] = doc.id
            resources.append(resource_data)
        
        logger.info(f"Recursos retornados: {len(resources)} recursos")
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Erro ao listar recursos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Assign a resource to a phase (main users only)
@app.post("/blocks/{block_id}/phases/{phase_id}/assign-resource")
async def assign_resource_to_phase(block_id: str, phase_id: str, update: PhaseUpdateResource, current_user: dict = Depends(require_main_role)):
    try:
        main_user_id = current_user['mainUserId']
        logger.info(f"Atribuindo recurso {update.resourceId} à fase {phase_id} no bloco {block_id}, mainUserId: {main_user_id}")
        
        block_ref = db.collection("blocks").document(block_id)
        block_doc = block_ref.get()
        if not block_doc.exists:
            logger.error(f"Bloco {block_id} não encontrado")
            raise HTTPException(status_code=404, detail="Bloco não encontrado")
        if block_doc.to_dict().get("mainUserId") != main_user_id:
            logger.error(f"Bloco {block_id} não pertence ao mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Acesso negado: Bloco não pertence ao usuário principal")

        phase_ref = block_ref.collection("phases").document(phase_id)
        phase_doc = phase_ref.get()
        if not phase_doc.exists:
            logger.error(f"Fase {phase_id} não encontrada")
            raise HTTPException(status_code=404, detail="Fase não encontrada")

        resource_ref = db.collection("resources").document(update.resourceId)
        resource_doc = resource_ref.get()
        if not resource_doc.exists:
            logger.error(f"Recurso {update.resourceId} não encontrado")
            raise HTTPException(status_code=404, detail="Recurso não encontrado")
        if resource_doc.to_dict().get("mainUserId") != main_user_id:
            logger.error(f"Recurso {update.resourceId} não pertence ao mainUserId {main_user_id}")
            raise HTTPException(status_code=403, detail="Acesso negado: Recurso não pertence ao usuário principal")

        phase_ref.update({"resourceId": update.resourceId})
        logger.info(f"Recurso {update.resourceId} atribuído à fase {phase_id}")
        return {"message": "Recurso atribuído à fase"}
    except Exception as e:
        logger.error(f"Erro ao atribuir recurso: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))