from fastapi import FastAPI

app = FastAPI()  #uvicorn main:app look for main.py file in instance app


@app.get("/")
async def root():
    return {"message": "Welcome to Planejafacil API"}