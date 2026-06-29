from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import clustering, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["cluster"])


class ClusterIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO", "c1ccccc1", "CCC"],
                "cutoff": 0.4,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=2000)
    cutoff: float = Field(0.4, ge=0.0, le=1.0)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/cluster")
def cluster_endpoint(
    body: ClusterIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Butina clustering by ECFP4 Tanimoto distance."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"cluster:{x_api_key}", limit=20, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        res = clustering.cluster(body.smiles, cutoff=body.cutoff)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/cluster", n)
    return {**res.to_dict(), "quota_charged": n}
