"""GraphQL API schema for Q-Mol using Strawberry."""
from __future__ import annotations
from typing import List, Optional

import strawberry
from strawberry.types import Info

from src import compute, predict, keys as keysdb
from src.dependencies import check_quota, record_usage


@strawberry.type
class Molecule:
    smiles: str
    mw: float
    logp: float
    qed: float


@strawberry.type
class ComputeResult:
    smiles: str
    mw: Optional[float]
    logp: Optional[float]
    tpsa: Optional[float]
    qed: Optional[float]
    hbd: Optional[int]
    hba: Optional[int]
    lipinski_pass: Optional[int]
    veber_pass: Optional[int]


@strawberry.type
class PredictionResult:
    smiles: str
    aqueous_logs: Optional[float]
    bbb_probability: Optional[float]
    herg_risk: Optional[float]
    gi_absorption: Optional[float]
    sa_score_lite: Optional[float]


@strawberry.type
class JobStatus:
    job_id: str
    status: str
    n_processed: int
    n_total: int


@strawberry.type
class Collection:
    id: str
    name: str
    owner_key: str
    description: Optional[str]
    is_public: bool


@strawberry.type
class Query:
    @strawberry.field
    def molecule(self, smiles: str) -> Molecule:
        result = compute.compute_molecule(-1, smiles)
        return Molecule(
            smiles=result.smiles,
            mw=result.mw or 0.0,
            logp=result.logp or 0.0,
            qed=result.qed or 0.0,
        )

    @strawberry.field
    def molecules(self, smiles_list: List[str]) -> List[Molecule]:
        return [self.molecule(s) for s in smiles_list]

    @strawberry.field
    def predict(self, smiles: str) -> PredictionResult:
        result = predict.predict_one(smiles)
        return PredictionResult(
            smiles=smiles,
            aqueous_logs=result.get("aqueous_logs"),
            bbb_probability=result.get("bbb_probability"),
            herg_risk=result.get("herg_risk"),
            gi_absorption=result.get("gi_absorption"),
            sa_score_lite=result.get("sa_score_lite"),
        )

    @strawberry.field
    def collections(self, api_key: str) -> List[Collection]:
        from src.collections import service as coll_service
        return [
            Collection(
                id=c.id, name=c.name, owner_key=c.owner_key,
                description=c.description, is_public=c.is_public,
            )
            for c in coll_service.list_collections(api_key)
        ]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def compute(self, smiles: str, api_key: str) -> ComputeResult:
        info = keysdb.lookup(api_key)
        if not info or not info.active:
            raise Exception("Invalid or inactive API key")
        check_quota(api_key, 1)
        result = compute.compute_molecule(-1, smiles)
        record_usage(api_key, "/graphql/compute", 1)
        return ComputeResult(
            smiles=result.smiles,
            mw=result.mw,
            logp=result.logp,
            tpsa=result.tpsa,
            qed=result.qed,
            hbd=result.hbd,
            hba=result.hba,
            lipinski_pass=result.lipinski_pass,
            veber_pass=result.veber_pass,
        )

    @strawberry.mutation
    def create_collection(self, api_key: str, name: str, description: Optional[str] = None) -> Collection:
        from src.collections import service as coll_service
        c = coll_service.create_collection(api_key, name, description)
        return Collection(
            id=c.id, name=c.name, owner_key=c.owner_key,
            description=c.description, is_public=c.is_public,
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
