from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Bridge-X RAG is Working!"}