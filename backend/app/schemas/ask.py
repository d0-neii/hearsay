from pydantic import BaseModel


class AskRequest(BaseModel):
    query: str
    stock_code: str | None = None
