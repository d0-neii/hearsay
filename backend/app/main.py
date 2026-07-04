from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.rag import ask

app = FastAPI(title="Hearsay API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 개발 서버
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    stock_code: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask_endpoint(body: AskRequest):
    try:
        result = ask(body.query, stock_code=body.stock_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
