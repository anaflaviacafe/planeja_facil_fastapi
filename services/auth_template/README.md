
## Autentication

Para criar usuários com e-mail e senha (como no endpoint /register-main), o provedor de autenticação de e-mail/senha deve estar habilitado. No firebase ir em autenticação método de login e abiilitar a opção:  Email/Senha


match /users/{mainUserId}: 

 Aplica-se à coleção users, onde cada documento tem um ID (mainUserId) correspondente ao ID de um usuário principal (geralmente o uid do Firebase Authentication).

 Permite leitura e escrita apenas se o usuario esta autenticado 
 Permite criar novos documentos em child_users apenas se o usuário autenticado for um main user (role == 'main') 

 ## Test 

 ### Registrar main
 ```
 curl -X POST http://localhost:8001/register-main -H "Content-Type: application/json" -d '{"name": "Ana Flavia Cafe", "email": "ana@test.com", "password": "senha123"}'

 no postman add a rota no metodo POST:
 http://localhost:8001/register-main
 e no body:

 {
    "name": "Ana Flavia Cafe",
    "email": "ana@test.com",
    "password": "senha123"
}
 ```

 Ao inserir um usuario principal, um token é gerado no firebase, esse token JWT deve ser usado para criar os childs etc
 O token deve conter as custom claims role: 'main' e mainUserId correspondente ao UID do usuário principal

 Para obter o token precisa fazer login

### Reuisição de login 
```
curl -X POST \
  "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=WEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ana@test.com",
    "password": "senha123",
    "returnSecureToken": true
  }'
```

Substituir WEB_API_KEY, no firebase nas configurações do projeto -> Geral copiar a chave de API Web, remover 

A resposta do login vai ser um json que tera o token de autentificação, exemplo:

```
{
  "idToken": "<JWT_TOKEN>",
  "refreshToken": "...",
  "expiresIn": "3600",
  "email": "joao@test.com",
  "localId": "<USER_UID>",
  ...
}
```
JWT_TOKEN  - sera o token

### Registrar Child
```
curl -X POST http://localhost:8001/child-users -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name": "Filho1", "email": "filho@test.com", "password": "senha456"}'
```

No token copiar JWT_TOKEN recebido no login do usuario principal, remover <>

### Listar Childs
```
curl -X GET http://localhost:8001/child-users -H "Authorization: Bearer <token>"
```

### Logar com Child
```
curl -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<WEB_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "filho@test.com",
    "password": "senha456",
    "returnSecureToken": true
  }'
```
Na resposta o "idToken": "<JWT_TOKEN>", tambem retorna no login do child. esse token que retorna pode ser usado para autenticar requisições do usuario filho


### Deletar usuario principal recursivamente
```
curl -X DELETE \
  'http://localhost:8001/users/main_user_id_here' \
  -H 'Authorization: Bearer token_here' \
  -H 'Content-Type: application/json'
```
No caso token ai seria do usuario main logado, mas como vou usar o firebase para excluir, adicionar um endpoint:
/admin/delete-user/{user_id} no FastAPI par apermitir que o admin delete o usuario recursivamente

File: admin.py, usando a rota nova para deletar com a chave da API, fica:
```
curl -X DELETE \
  'http://localhost:8001/admin/delete-user/main_user_id_here' \
  -H 'X-Admin-API-Key: ADMIN_API_KEY' \
  -H 'Content-Type: application/json'
```

### Logout

É usualmente implementado no frontend descartando o token, mas poderia criar uma rota se quisse de logout:

### Main user edit/update child user

Login com main, obter token do child listando os usuarios, pegar o id do usuario que deseja

Para atulizar:
```
curl -X PUT http://localhost:8001/child-users/<CHILD_USER_UID> \
  -H "Authorization: Bearer <JWT_TOKEN_DO_USUARIO_PRINCIPAL>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Filho1 Atualizado"}'
``` 

## Token

Firebase Authentication, os tokens JWT (idToken) têm um tempo de expiração padrão de 1 hora (3600 segundos)

### Usar refresh tokens para renovar o idToken

Na resposta da requisição de login vem um "refreshToken": "<REFRESH_TOKEN>",  tem que copiar esse refresh token, e suar o endpoint /token da API REST do firebase oara obter um novo idToken:
```
curl -X POST "https://securetoken.googleapis.com/v1/token?key=<WEB_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "refresh_token",
    "refresh_token": "<REFRESH_TOKEN>"
  }'
```

Resposta esperada:
```
{
  "access_token": "<NOVO_ID_TOKEN>",
  "expires_in": "3600",
  "token_type": "Bearer",
  "refresh_token": "<NOVO_REFRESH_TOKEN>",
  "id_token": "<NOVO_ID_TOKEN>",
  "user_id": "<USER_UID>",
  "project_id": "<PROJECT_ID>"
}
```

Para automatizar a renovação do token pode criar uma rota no fastAPI /refresh-token

```
curl -X POST http://localhost:8001/refresh-token \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<REFRESH_TOKEN>"}'
```


### Template Routes

```
curl -H "Authorization: Bearer <token>" http://localhost:8001/templates

curl -X POST -H "Authorization: Bearer <token>" http://localhost:8001/select-template/<template_id>

curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":"Teste","holidays":{"holidays":
[{"date":"2025-12-25T00:00:00","name":"Natal"}]},"weekStart":1,"weekEnd":5,"shifts":[{"entry":"08:00:00","exit":"17:00:00"}]}' http://localhost:8001/templates

curl -X DELETE -H "Authorization: Bearer <token>" http://localhost:8001/templates/<template_id>
```



