from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated, Any

from src.collections import service as coll_service
from src import keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["collections"])


class CollectionCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "My Project", "description": "Lead molecules"}}
    )
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CollectionUpdateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "Updated Name", "is_public": True}}
    )
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class CollectionItemIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": "CCO", "name": "Ethanol", "notes": "Solvent", "properties": {"source": "lab"}}}
    )
    smiles: str = Field(..., min_length=1)
    name: str | None = None
    notes: str | None = None
    properties: dict[str, Any] | None = None

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


class ShareIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"shared_with_key": "qmol_xxx", "role": "viewer"}}
    )
    shared_with_key: str = Field(..., min_length=1)
    role: str = Field("viewer", min_length=1)


def _require_auth(x_api_key: str | None) -> str:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return x_api_key


@router.post("/collections")
def create_collection(
    body: CollectionCreateIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    c = coll_service.create_collection(key, body.name, body.description)
    return {"collection": c.to_dict()}


@router.get("/collections")
def list_collections(
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    collections = coll_service.list_collections(key)
    return {"collections": [c.to_dict() for c in collections]}


@router.get("/collections/{collection_id}")
def get_collection(
    collection_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access:
        raise HTTPException(status_code=404, detail="Collection not found")
    c = coll_service.get_collection(collection_id)
    items = coll_service.get_collection_items(collection_id)
    return {
        "collection": c.to_dict() if c else None,
        "items": [i.to_dict() for i in items],
        "role": role,
    }


@router.post("/collections/{collection_id}/items")
def add_item(
    collection_id: str,
    body: CollectionItemIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access or role == "viewer":
        raise HTTPException(status_code=403, detail="Not allowed to modify this collection")
    item = coll_service.add_item(collection_id, body.smiles, body.name, body.notes, body.properties)
    return {"item": item.to_dict()}


@router.delete("/collections/{collection_id}/items/{item_id}")
def remove_item(
    collection_id: str,
    item_id: int,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access or role == "viewer":
        raise HTTPException(status_code=403, detail="Not allowed to modify this collection")
    ok = coll_service.remove_item(collection_id, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"removed": True}


@router.put("/collections/{collection_id}")
def update_collection(
    collection_id: str,
    body: CollectionUpdateIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access or role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Not allowed to modify this collection")
    c = coll_service.update_collection(
        collection_id, name=body.name, description=body.description, is_public=body.is_public
    )
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"collection": c.to_dict()}


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access or role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can delete")
    ok = coll_service.delete_collection(collection_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"deleted": True}


@router.post("/collections/{collection_id}/share")
def share_collection(
    collection_id: str,
    body: ShareIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, role = coll_service.can_access(collection_id, key)
    if not can_access or role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can share")
    if not keysdb.lookup(body.shared_with_key):
        raise HTTPException(status_code=404, detail="Target API key not found")
    ok = coll_service.share_collection(collection_id, body.shared_with_key, body.role)
    return {"shared": ok}


@router.get("/collections/{collection_id}/export")
def export_collection(
    collection_id: str,
    format: str = "csv",
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    key = _require_auth(x_api_key)
    can_access, _ = coll_service.can_access(collection_id, key)
    if not can_access:
        raise HTTPException(status_code=404, detail="Collection not found")
    if format not in ("csv", "sdf", "parquet"):
        raise HTTPException(status_code=400, detail="Format must be csv, sdf, or parquet")
    try:
        result = coll_service.export_collection(collection_id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result
