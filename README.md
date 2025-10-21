### Commands

```
pip install fastapi uvicorn

pip install google-cloud-firestore

docker-compose up --build

docker-compose build --no-cache

ls -R /app   #checar conteudo volume app

docker-compose logs

docker-compose down
```

### Tree

```

D:\USP\TCC\planeja_facil_fastapi\
├── secrets/                          # Credenciais do Firebase (não commitar)
│   └── key.json
├── services/                         # Pastas para microserviços
│   ├── auth_template/                # Serviço de usuário + template (porta 8001)
│   │   ├── main.py                   # Rotas de login, usuários, templates
│   │   └── Dockerfile
│   ├── full_block/      # Serviço de cadastro de blocos/fases/recursos (porta 8002)
│   │   ├── main.py                   # Rotas para CRUD de blocos, fases, recursos
│   │   └── Dockerfile
│   └── production_orders/            # Serviço de ordens de produção + apontamentos (porta 8003)
│       ├── main.py                   # Rotas para OPs, escalonamento, apontamentos
│       └── Dockerfile
├── shared/                           # Compartilhado entre serviços (Firebase init)
│   └── config.py
|   └── auth.py  
├── .env                              # Variáveis comuns (FIREBASE_CREDENTIALS_PATH, etc.)
├── docker-compose.yaml               # Configuração de todos os containers
├── Dockerfile                        # Para o app principal (se necessário)
├── main.py                           # Para o app principal (ex.: roteador geral ou health check)
├── requirements.txt                  # Dependências comuns (fastapi, uvicorn, firebase-admin, etc.)
└── .gitignore                        # Ignore secrets, .env, etc.
```

### Firebase

https://console.firebase.google.com/?pli=1

No Console Firebase, com seu projeto aberto:

Vá no menu lateral esquerdo e clique em "Cloud Firestore".

Clique em "Iniciar coleção" (ou "Start collection").

No campo ID da coleção, digite o nome da sua coleção.

Exemplo: usuarios, templete,  etc. Clique em "Avançar".

Depois de criar as tabelas, no menu lateral, clique em Configurações do Projeto -> Contas de serviço -> Gerar nova chave privada 
Baixar o json e adicionar a configuração do SDK dada no firebase no projeto.

 - Custom claims

   São declarações personalizadas, campos que personalizados que pode adicionar token  de autentificação, para armazenar informações como nivel de acesso, plano de assinatura, etc. Na prática serve para controlar permissões por função (ex: role: 'main',  role: 'admin')
   No caso quando inserir um usuario principal a função deve definir os claims. Se definir no firebase deve tambem configurar os claims. acessando as custom claims com request.auth.token
  
   O token de autenticação não se atualiza automaticamente, é necessário que o usuário faça logout e login novamente, ou que forçe a atulização do token no app do cliente.
   As claims devem ser dados simples (string, boolean, número); não objetos complexos

   Quando cria um usuário no firebase e define isMain: true, o não claim não é configurado, somente é configurado na função de inserir um usuario na api.
   TOD: Pensar se faço um criar usuario na primeira instalação ou se mando o comando numa rota pela postman para cria-lo!


No projeto planeja-facil, no menu à esquerda, clique em Firestore Database. Clique na aba Rules (Regras)
Tera um editor de texto com regras padrão, substitua o codigo pela regra:

### Rules

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Templates: Only main users can read/write their own templates
    match /templates/{templateId} {
      allow read, write: if request.auth != null && 
                          request.auth.token.role == 'main' && 
                          resource.data.mainUserId == userId;
    }

    // Users: Each user can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;

      // Child users: Main users can create/read, child users can only read their own data
      match /child_users/{childId} {
        allow read: if request.auth != null && 
                     (request.auth.uid == childId || 
                      (request.auth.token.role == 'main' && 
                       request.auth.token.mainUserId == userId));
        allow create: if request.auth != null && 
                      request.auth.token.role == 'main' && 
                      request.auth.token.mainUserId == userId;
        allow update, delete: if false; // Block updates/deletes for now
      }
    }

    // Blocks: Main and child users can read, only main users can write
    match /blocks/{blockId} {
      allow read: if request.auth != null && 
                   resource.data.mainUserId == request.auth.token.mainUserId;
      allow write, delete: if request.auth != null && 
                    request.auth.token.role == 'main' && 
                    resource.data.mainUserId == request.auth.token.mainUserId;

      // Phases subcollection
      match /phases/{phaseId} {
        allow read: if request.auth != null && 
                     resource.data.mainUserId == request.auth.token.mainUserId;
        allow write: if request.auth != null && 
                      request.auth.token.role == 'main' && 
                      resource.data.mainUserId == request.auth.token.mainUserId;
      }
    }

    // Resources
    match /resources/{resourceId} {
      allow read: if request.auth != null && 
                   resource.data.mainUserId == request.auth.token.mainUserId;
      allow write: if request.auth != null && 
                    request.auth.token.role == 'main' && 
                    resource.data.mainUserId == request.auth.token.mainUserId;
    }

    // Resources type
    match /resourcesTypes/{typeId} {
        allow read: if request.auth != null && request.auth.uid == userId;
        allow create: if request.auth != null && request.auth.uid == userId;
        allow delete: if request.auth != null && request.auth.uid == userId
                      && resource.data.isDefault == false;
      }
  }
}
```


### .env
FIREBASE_CREDENTIALS_PATH=/secrets/nomeKeyFirebaseAqui.json
FIREBASE_DATABASE_URL=url firebase aqui
WEB_API_KEY=chave api aqui
ADMIN_API_KEY=chave admin api aqui

#### ADMIN_API_KEY

Criar um admin api key usando um uuid randomico ou um string dificil como:

Ex: 
import uuid
print(uuid.uuid4())

ADMIN_API_KEY=123e4567-e89b-12d3-a456-426614174000

poderia ser um string como 32–64 characters:

ADMIN_API_KEY=fk459fkdsjfPlan_dsa97fjfd_EasyanaApp

No docker-compose.yml carrega  .env e carrega essa chave 


### Endpoints

 - service app http://localhost:8000  
 - service users http://localhost:8001/users
```
### Imagem Docker

 As imagens Docker são criadas a partir dos Dockerfiles e do docker-compose.yaml

 Construir as imagens
 ```
 docker-compose build
 docker images

 PS D:\USP\TCC\planeja_facil_fastapi> docker images
 REPOSITORY                            TAG       IMAGE ID       CREATED          SIZE
 planeja_facil_fastapi-app             latest    60c91e56b3e9   20 seconds ago   1.83GB
 planeja_facil_fastapi-users_service   latest    72406e53820b   2 minutes ago    1.83GB
 ```
 Salvar as imagens como arquivos .tar
 ```
 docker save -o planeja_facil_app.tar planeja_facil_fastapi-app:latest
 docker save -o planeja_facil_users.tar planeja_facil_fastapi-users_service:latest
 ```
 Criar um arquivo chamado docker-compose-cliente.yaml para o cliente 


Testar:
```
 docker-compose -f docker-compose-cliente.yaml up -d

 docker ps
 docker ps -a

 docker-compose -f docker-compose-cliente.yaml down
```

Verificar logs:
```
docker-compose logs users_service
```

Sync timer ALL containers
```
docker-compose exec auth_template sh -c "apt-get update -qq && apt-get install -y ntpdate && ntpdate -s time.nist.gov && date +%s"
```
Com o conteiner rodando da pra ver que ta com erro na hora atual:

D:\USP\TCC\planeja_facil_fastapi>docker exec -it planeja_facil_auth_template date
Fri Oct 17 17:42:37 UTC 2025    
UTC do conteiner é 3h a mais exatas