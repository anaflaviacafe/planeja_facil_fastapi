from fastapi import HTTPException
from shared.config import db
from shared.config import logger

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
    #template_ref = db.collection('templates').document(template_id)
    template_ref = (db.collection('users').document(main_user_id).collection('templates').document(template_id))

    template_doc = template_ref.get()
    if not template_doc.exists:
        logger.error(f"Template {template_id} not found")
        raise HTTPException(status_code=404, detail="Template not found")
    if template_doc.to_dict().get('user_id') != main_user_id:
        logger.error(f"Template {template_id} does not belong to mainUserId {main_user_id}")
        raise HTTPException(status_code=403, detail="Access denied: Template does not belong to the main user")
