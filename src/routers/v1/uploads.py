from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from typing import Annotated

from src import uploads, keys as keysdb, compute, result_cache
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["uploads"])


@router.post("/upload/compute")
async def upload_compute(
    file: UploadFile = File(...),
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Accept SDF/CSV/SMI, return descriptors."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"upload:{x_api_key}", limit=10, window=60.0)
    blob = await file.read()
    if len(blob) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (>50MB)")
    parsed = uploads.parse(blob, filename=file.filename or "")
    if not parsed.smiles:
        raise HTTPException(status_code=400, detail="No valid molecules parsed")
    used, quota = check_quota(x_api_key, len(parsed.smiles))
    results = [compute.compute_molecule(cid=-(i + 1), smiles=s).to_dict()
               for i, s in enumerate(parsed.smiles)]
    record_usage(x_api_key, "/upload/compute", len(parsed.smiles))
    return {
        "format": parsed.format,
        "n_parsed": parsed.n_parsed,
        "results": results,
        "quota_charged": len(parsed.smiles),
    }
