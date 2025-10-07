
## Test 

### List blocks

```
curl -X GET http://localhost:8002/blocks \
-H "Authorization: Bearer <main_user_jwt_token>"
```

### Create block
```
curl -X POST http://localhost:8001/blocks \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <main_user_jwt_token>" \
-d '{"name": "Block A", "description": "Description of Block A", "templateName": "Template 1"}'
```

### Create Phase
```
curl -X POST http://localhost:8001/blocks/<block_id>/phases \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <main_user_jwt_token>" \
-d '{"name": "Phase 1", "description": "Description of Phase 1", "duration": 2.5, "templateName": "Template 1"}'
```

### Link Resource
```
curl -X POST http://localhost:8001/blocks/<block_id>/phases/<phase_id>/assign-resource \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <main_user_jwt_token>" \
-d '{"resourceId": "<resource_id>"}'
```