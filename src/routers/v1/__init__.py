"""Q-Mol API v1 router aggregation.

All sub-routers are imported here and mounted under the `/v1` prefix.
"""
from fastapi import APIRouter

from .compute import router as compute_router
from .descriptors import router as descriptors_router
from .similarity import router as similarity_router
from .screen import router as screen_router
from .predict import router as predict_router
from .fingerprints import router as fingerprints_router
from .cluster import router as cluster_router
from .jobs import router as jobs_router
from .convert import router as convert_router
from .tautomers import router as tautomers_router
from .conformers import router as conformers_router
from .standardize import router as standardize_router
from .formula import router as formula_router
from .reactions import router as reactions_router
from .scaffolds import router as scaffolds_router
from .retro import router as retro_router
from .substructure import router as substructure_router
from .diversity import router as diversity_router
from .mcs import router as mcs_router
from .charges import router as charges_router
from .alerts import router as alerts_router
from .stereoisomers import router as stereoisomers_router
from .shape3d import router as shape3d_router
from .dedup import router as dedup_router
from .admin import router as admin_router
from .billing import router as billing_router
from .teams import router as teams_router
from .uploads import router as uploads_router
from .webhooks import router as webhooks_router
from .health import router as health_router
from .misc import router as misc_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(compute_router)
v1_router.include_router(descriptors_router)
v1_router.include_router(similarity_router)
v1_router.include_router(screen_router)
v1_router.include_router(predict_router)
v1_router.include_router(fingerprints_router)
v1_router.include_router(cluster_router)
v1_router.include_router(jobs_router)
v1_router.include_router(convert_router)
v1_router.include_router(tautomers_router)
v1_router.include_router(conformers_router)
v1_router.include_router(standardize_router)
v1_router.include_router(formula_router)
v1_router.include_router(reactions_router)
v1_router.include_router(scaffolds_router)
v1_router.include_router(retro_router)
v1_router.include_router(substructure_router)
v1_router.include_router(diversity_router)
v1_router.include_router(mcs_router)
v1_router.include_router(charges_router)
v1_router.include_router(alerts_router)
v1_router.include_router(stereoisomers_router)
v1_router.include_router(shape3d_router)
v1_router.include_router(dedup_router)
v1_router.include_router(admin_router)
v1_router.include_router(billing_router)
v1_router.include_router(teams_router)
v1_router.include_router(uploads_router)
v1_router.include_router(webhooks_router)
v1_router.include_router(health_router)
v1_router.include_router(misc_router)
