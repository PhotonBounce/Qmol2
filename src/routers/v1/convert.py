from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated, Any

from src import convert, keys as keysdb
from src.export import formats as export_formats
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["convert"])


class ConvertIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO"],
                "input_format": "smiles",
                "with_molblock": False,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=10000)
    input_format: str = Field("smiles", min_length=1)
    with_molblock: bool = False

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


class SingleConvertIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": "CCO"}}
    )
    smiles: str = Field(..., min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


class FDAConvertIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": "CCO", "properties": {"name": "Ethanol", "cas": "64-17-5"}}}
    )
    smiles: str = Field(..., min_length=1)
    properties: dict[str, Any] | None = None

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


def _authenticate(x_api_key: str | None) -> None:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")


@router.post("/convert")
def convert_endpoint(
    body: ConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert to canonical SMILES + InChI + InChIKey (+ optional MolBlock)."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        results = convert.convert_batch(
            body.smiles, input_format=body.input_format,
            with_molblock=body.with_molblock,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert", n)
    return {"results": results, "quota_charged": n}


@router.post("/convert/pdb")
def convert_pdb(
    body: SingleConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert SMILES to PDB format with 3D coordinates."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        pdb = export_formats.smiles_to_pdb(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/pdb", 1)
    return {"pdb": pdb, "quota_charged": 1}


@router.post("/convert/mol2")
def convert_mol2(
    body: SingleConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert SMILES to MOL2 (Tripos) format with 3D coordinates."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        mol2 = export_formats.smiles_to_mol2(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/mol2", 1)
    return {"mol2": mol2, "quota_charged": 1}


@router.post("/convert/cif")
def convert_cif(
    body: SingleConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert SMILES to CIF (Crystallographic Information File) format."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        cif = export_formats.smiles_to_cif(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/cif", 1)
    return {"cif": cif, "quota_charged": 1}


@router.post("/convert/inchi")
def convert_inchi(
    body: SingleConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert SMILES to InChI and InChIKey."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        result = export_formats.smiles_to_inchi(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/inchi", 1)
    return {**result, "quota_charged": 1}


@router.post("/convert/fda")
def convert_fda(
    body: FDAConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Generate FDA submission-ready molecular description."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        report = export_formats.generate_fda_report(body.smiles, body.properties)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/fda", 1)
    return {"fda_report": report, "quota_charged": 1}


@router.post("/convert/cdx")
def convert_cdx(
    body: SingleConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert SMILES to ChemDraw CDX format (base64-encoded MolBlock placeholder)."""
    _authenticate(x_api_key)
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        cdx = export_formats.smiles_to_cdx(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert/cdx", 1)
    return {"cdx_base64": cdx, "quota_charged": 1}
