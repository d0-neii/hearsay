from fastapi import APIRouter, HTTPException

from app.rag import ask as rag_ask
from app.schemas.ask import AskRequest

router = APIRouter()


@router.post("/ask")
def ask_endpoint(body: AskRequest):
    try:
        result = rag_ask(body.query, stock_code=body.stock_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
