"""Minimal FastAPI app for the independent OVK consumer gate."""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="OVK Consumer FastAPI", version="0.1.0")


class Item(BaseModel):
    name: str
    owner: str


def require_admin(role: str = "user") -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return role


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin/export")
def admin_export(_role: str = Depends(require_admin)) -> dict[str, str]:
    return {"export": "redacted"}


@app.post("/items")
def create_item(item: Item) -> Item:
    return item
