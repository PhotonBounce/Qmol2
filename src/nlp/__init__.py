"""Natural language query module for Q-Mol.

Exports the parser and an executor that dispatches parsed queries
to the appropriate internal functions.
"""
from __future__ import annotations

from .parser import parse_query

__all__ = ["parse_query", "execute_query"]


def execute_query(query: str) -> dict:
    """Parse and execute a natural language chemistry query.

    Dispatches to the appropriate internal function based on the
    parsed endpoint. Returns a unified result dict.
    """
    parsed = parse_query(query)
    endpoint = parsed.get("endpoint", "compute")
    params = parsed.get("params", {})
    filters = parsed.get("filters", {})

    result: dict = {"parsed": parsed, "results": None}

    if endpoint == "similarity":
        from src import similarity, storage
        import config

        query_smiles = params.get("query_smiles", "c1ccccc1")
        top_k = params.get("top_k", 20)
        conn = storage.connect(config.DB_PATH)
        try:
            hits = similarity.search(conn, query_smiles, top_k=top_k)
            result["results"] = [h.to_dict() for h in hits]
        finally:
            conn.close()

    elif endpoint == "generate":
        from src.generation import sample_smiles

        seed_smiles = params.get("seed_smiles", ["c1ccccc1"])
        n = params.get("n", 10)
        generated = sample_smiles(seed_smiles, n=n)
        result["results"] = {"generated": generated, "count": len(generated)}

    elif endpoint == "predict":
        from src import predict

        smiles_list = params.get("smiles", ["c1ccccc1"])
        results = [predict.predict_one(s).to_dict() for s in smiles_list]
        result["results"] = results

    elif endpoint == "optimize":
        from src.generation import optimizer

        smiles = params.get("smiles", "c1ccccc1")
        target_property = params.get("target_property", "QED")
        target_defaults = {
            "QED": 0.9,
            "logP": 2.5,
            "MW": 400.0,
            "TPSA": 90.0,
        }
        target_value = target_defaults.get(target_property, 0.9)
        result["results"] = optimizer.optimize_molecule(
            smiles, target_property, target_value
        )

    elif endpoint == "compute":
        from src import compute

        smiles_list = params.get("smiles", ["c1ccccc1"])
        results = [
            compute.compute_molecule(cid=-(i + 1), smiles=s).to_dict()
            for i, s in enumerate(smiles_list)
        ]
        result["results"] = results

    if filters:
        result["filters"] = filters

    return result
