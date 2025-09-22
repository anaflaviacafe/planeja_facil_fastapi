### Commands

```
pip install fastapi uvicorn

docker-compose up --build

docker-compose build --no-cache

ls -R /app   #checar conteudo volume app

docker-compose logs

docker-compose down
```

### Tree

```

planeja_facil_fastapi/
├── .env
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
├── main.py
├── README.md
├── requirements.txt
├── services/
│   ├── users/
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   ├── README.md
├── shared/
│   ├── config.py
│   ├── serviceAccountKey.json

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

### .env
FIREBASE_CREDENTIALS_PATH=/secrets/nomeKeyFirebaseAqui.json
FIREBASE_DATABASE_URL=url firebase aqui
WEB_API_KEY=chave api aqui

### Endpoints

 - service app http://localhost:8000  
 - service users http://localhost:8001/users

 ## Imagem Docker

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