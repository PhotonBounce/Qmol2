# Q-Mol Quantum Tier Documentation

## Overview

The Q-Mol **Quantum Tier** provides quantum-computed molecular energies using the
Variational Quantum Eigensolver (VQE) algorithm. It fulfills the
"quantum-verified" brand promise by producing cryptographically-signed
provenance certificates for every quantum calculation.

> **Important:** Classical CCSD (coupled cluster with single and double
> excitations) remains the ground-truth energy. VQE is a **signature stamp**
> that verifies the molecule on a quantum circuit, providing an additional
> layer of trust and auditability.

---

## How VQE Works

1. **Molecular Hamiltonian** — PySCF builds the electronic-structure Hamiltonian
   in second-quantized form from the molecule's 3D geometry.
2. **Qubit Mapping** — The Jordan-Wigner mapper converts fermionic operators to
   qubit operators (Pauli strings). Each spatial orbital requires 2 qubits
   (spin-up and spin-down).
3. **Ansatz** — The Unitary Coupled Cluster with Singles and Doubles (UCCSD)
   ansatz prepares a trial wavefunction on the quantum processor. The Hartree-
   Fock state is used as the initial reference.
4. **Optimization** — The SLSQP classical optimizer adjusts the ansatz
   parameters to minimize the energy expectation value.
5. **Result** — The converged energy is returned alongside a SHA-256 circuit
   hash that uniquely identifies the optimized quantum circuit.

### H₂ Benchmark

For H₂ with the sto-3g basis, the exact FCI energy is approximately
**−1.137 Ha**. VQE with UCCSD converges to within **0.001 Ha** of this
value on a noiseless simulator.

---

## Setup

### 1. Install Quantum Dependencies

```bash
# Core quantum stack (Linux/macOS recommended; Windows use WSL)
pip install qiskit>=1.0 qiskit-nature>=0.7 qiskit-algorithms>=0.3 \
            qiskit-ibm-runtime>=0.23 pyscf>=2.6
```

> **Windows users:** PySCF requires BLAS/LAPACK. Use `conda-forge`:
> `conda install -c conda-forge pyscf`.

### 2. Configure IBM Quantum (Optional)

To submit jobs to IBM Quantum hardware:

1. Create an account at [https://quantum.ibm.com](https://quantum.ibm.com)
2. Copy your API token
3. Set the environment variable:

```bash
export IBM_QUANTUM_TOKEN="your-token-here"
```

Or add it to `.env`:

```
IBM_QUANTUM_TOKEN=your-token-here
```

### 3. Configure AWS Braket (Optional)

```bash
export AWS_BRAKET_ROLE_ARN="arn:aws:iam::ACCOUNT:role/BraketRole"
```

---

## API Endpoints

### `POST /v1/compute/quantum`

Run quantum-certified VQE for a batch of molecules.

**Request**

```json
{
  "smiles": ["[H]"],
  "basis": "sto-3g",
  "backend": "local"
}
```

| Field   | Type     | Default   | Description                           |
|---------|----------|-----------|---------------------------------------|
| smiles  | string[] | required  | SMILES strings (max 500)              |
| basis   | string   | "sto-3g"  | Basis set for Hamiltonian             |
| backend | string   | "local"   | `"local"`, `"ibm"`, or `"aws"`        |

**Pricing:** 50× per molecule (charged against API quota).

**Response**

```json
{
  "results": [
    {
      "smiles": "[H]",
      "method": "VQE-Qiskit",
      "energy_hartree": -1.137,
      "classical_energy_hartree": -1.137,
      "vqe_energy_hartree": -1.137,
      "vqe_method": "VQE-Qiskit",
      "vqe_circuit_hash": "a1b2c3d4...",
      "vqe_num_qubits": 4,
      "quantum_job_id": "q_abc123...",
      "quantum_certificate": {
        "job_id": "q_abc123...",
        "smiles": "[H]",
        "circuit_hash": "a1b2c3d4...",
        "energy_hartree": -1.137,
        "timestamp": "2026-06-29T12:00:00Z",
        "backend": "local",
        "basis": "sto-3g",
        "verification_url": "https://qmol.app/verify/q_abc123...",
        "signature": "sha256..."
      }
    }
  ],
  "backend_used": "local",
  "charge_per_molecule": 50
}
```

### `GET /v1/compute/quantum/{job_id}/certificate`

Download the provenance certificate for a completed quantum job.

**Response:** The certificate JSON (see above).

### `GET /v1/quantum/status`

Check IBM Quantum queue status.

**Response**

```json
{
  "qiskit_available": true,
  "ibm_status": {
    "available": true,
    "backends": [
      {"name": "ibm_brisbane", "operational": true, "pending_jobs": 12}
    ]
  }
}
```

---

## Interpreting Results

| Field                    | Meaning                                                            |
|--------------------------|--------------------------------------------------------------------|
| `energy_hartree`         | Primary energy (VQE when quantum tier is used, otherwise CCSD)   |
| `classical_energy_hartree` | PySCF CCSD/FCI ground truth — always the reference               |
| `vqe_energy_hartree`     | VQE variational energy (should be ≥ classical, within ~1 mHa)     |
| `vqe_circuit_hash`       | SHA-256 of the optimized circuit QASM — the "quantum signature"   |
| `vqe_num_qubits`         | Number of qubits used for the Jordan-Wigner mapping              |
| `quantum_certificate`    | Cryptographically signed JSON for third-party verification         |

### Accuracy Guidelines

- **H₂ (4 qubits):** VQE ≈ FCI to within 0.001 Ha
- **LiH (8 qubits):** VQE ≈ FCI to within 0.005 Ha
- **Larger molecules (>12 qubits):** VQE is skipped; classical CCSD is used

---

## Cloud Fallback

If the IBM Quantum queue exceeds 200 pending jobs (estimated > 1 hour wait),
the system automatically falls back to the **local Qiskit simulator** and
returns a `fallback_recommended: true` flag in the response.

You can also pre-check queue status:

```python
from src import quantum
status = quantum.cloud.get_ibm_queue_status()
print(status["backends"][0]["pending_jobs"])
```

---

## Pricing

| Tier        | Charge per molecule | Description                      |
|-------------|---------------------|----------------------------------|
| Classical   | 1×                  | RDKit + PySCF CCSD               |
| Quantum     | 50×                 | VQE + provenance certificate     |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  SMILES Input   │────▶│  RDKit geometry  │────▶│  PySCF Hamilton │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
            ┌─────────────────┐
            │  Jordan-Wigner  │
            │  qubit mapping  │
            └─────────────────┘
                    │
                    ▼
            ┌─────────────────┐     ┌─────────────────┐
            │  UCCSD ansatz   │────▶│  VQE optimizer  │
            │  (Qiskit)       │     │  (SLSQP)        │
            └─────────────────┘     └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  Circuit hash   │
                                    │  + Certificate  │
                                    └─────────────────┘
```

---

## Support

For questions about quantum calculations, certificate verification, or IBM
Quantum setup, contact the Q-Mol team or open an issue on the repository.

---

*Last updated: 2026-06-29*
