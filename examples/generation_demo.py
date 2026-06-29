"""De novo molecular generation engine demo for Q-Mol.

Run this script in an environment where RDKit is installed:
    python examples/generation_demo.py
"""
from src.generation import rnn_generator, optimizer, scorer
from rdkit import Chem

# ============================================================
# 1. SMILES Generation (Markov model trained on seed library)
# ============================================================
SEEDS = [
    "CCO",  # ethanol
    "c1ccccc1",  # benzene
    "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # caffeine
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # ibuprofen
    "c1ccc2c(c1)c(cn2)CCN",  # tryptamine fragment
    "CC(C)NCC(COc1ccccc1)O",  # propranolol-like
    "c1ccccc1CCN",  # phenethylamine
]

print("=== 1. Generating novel molecules ===")
generated = rnn_generator.sample_smiles(SEEDS, n=20)
for i, smi in enumerate(generated[:5], 1):
    mol = Chem.MolFromSmiles(smi)
    mw = Chem.Descriptors.MolWt(mol)
    logp = Chem.Descriptors.MolLogP(mol)
    print(f"  {i}. {smi}  |  MW={mw:.1f}  logP={logp:.2f}")
print(f"Total generated: {len(generated)}\n")

# ============================================================
# 2. Single-objective optimization (tune logP toward 2.5)
# ============================================================
print("=== 2. Single-objective optimization ===")
result = optimizer.optimize_molecule(
    smiles="c1ccccc1CCN",  # phenethylamine
    target_property="logP",
    target_value=2.5,
    max_steps=30,
    population_size=10,
)
print(f"Original:  {result['original_smiles']}  (score={result['original_score']:.3f})")
print(f"Optimized: {result['optimized_smiles']}  (score={result['optimized_score']:.3f})")
print(f"Steps: {result['steps']}\n")

# ============================================================
# 3. Multi-objective lead optimization
# ============================================================
print("=== 3. Multi-objective lead optimization ===")
lead_result = optimizer.optimize_lead(
    smiles="c1ccccc1CCN",
    objectives={
        "logP": (2.5, 1.0),
        "MW": (350, 50),
        "QED": (0.7, 0.3),
    },
    max_steps=40,
    population_size=10,
)
print(f"Original:  {lead_result['original_smiles']}  (score={lead_result['original_score']:.3f})")
print(f"Optimized: {lead_result['optimized_smiles']}  (score={lead_result['optimized_score']:.3f})")
print(f"Steps: {lead_result['steps']}\n")

# ============================================================
# 4. Multi-objective scoring
# ============================================================
print("=== 4. Multi-objective scoring ===")
mol = Chem.MolFromSmiles(lead_result['optimized_smiles'])
score = scorer.multi_objective_score(
    mol,
    objectives={
        "logP": scorer.logp_objective(2.5, 1.0),
        "MW": scorer.mw_objective(350, 50),
        "QED": scorer.qed_objective(),
        "synth": scorer.synthesizability_objective(),
        "lipinski": scorer.lipinski_objective(),
    },
    weights={"QED": 2.0, "lipinski": 1.5, "logP": 1.0, "MW": 1.0, "synth": 0.5},
)
print(f"Desirability: {score['desirability']:.3f}")
for name, val in score["scores"].items():
    print(f"  {name}: {val:.3f}")

print("\n=== Demo complete ===")
