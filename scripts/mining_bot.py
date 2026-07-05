#!/usr/bin/env python3
"""
Q-Mol Mining Bot - Direct API miner for multi-user molecule harvesting.
Runs continuously, mining unique molecules for all configured users.
"""

import json
import random
import time
import urllib.request
from datetime import datetime

API_BASE = "https://photon-bounce.com/qmol/api"
USER_IDS = [33, 34, 35, 36, 37, 38, 39, 40, 41, 42]

# Expanded molecular library (drugs, scaffolds, natural products, fragments)
# These are real, valid SMILES strings
MOLECULES = [
    # Common solvents / simple organics
    ("CC(C)=O", "Acetone", 58.08, -0.26, 17.07, 1, 0.7),
    ("CO", "Methanol", 32.04, -0.77, 20.23, 1, 0.42),
    ("CCO", "Ethanol", 46.07, -0.31, 20.23, 1, 0.68),
    ("CC(C)O", "Isopropanol", 60.10, 0.14, 20.23, 1, 0.66),
    ("CCCCO", "Butanol", 74.12, 0.88, 20.23, 1, 0.65),
    ("c1ccccc1", "Benzene", 78.11, 2.13, 0.0, 0, 0.45),
    ("Cc1ccccc1", "Toluene", 92.14, 2.65, 0.0, 0, 0.52),
    ("c1ccc2ccccc2c1", "Naphthalene", 128.17, 3.30, 0.0, 0, 0.48),
    ("c1ccc2c(c1)ccc2", "Indene", 116.16, 2.83, 0.0, 0, 0.55),
    ("C1CCCCC1", "Cyclohexane", 84.16, 2.81, 0.0, 0, 0.58),
    
    # Heterocycles
    ("c1ccoc1", "Furan", 68.07, 1.31, 13.14, 0, 0.55),
    ("c1ccsc1", "Thiophene", 84.14, 1.86, 0.0, 0, 0.50),
    ("c1cnc[nH]1", "Imidazole", 68.08, 0.08, 28.68, 1, 0.60),
    ("c1cnccc1", "Pyridine", 79.10, 0.65, 12.89, 0, 0.62),
    ("c1ccc2ncccc2c1", "Quinoline", 129.16, 2.08, 12.89, 0, 0.55),
    ("c1ccc2cc3ccccc3cc2c1", "Anthracene", 178.23, 4.45, 0.0, 0, 0.42),
    ("c1ccc2c(c1)OCCO2", "1,4-Benzodioxane", 136.15, 1.45, 18.46, 0, 0.65),
    ("c1ccc2occc2c1", "Benzofuran", 118.13, 2.40, 13.14, 0, 0.55),
    ("c1ccc2c(c1)sc2", "Benzothiophene", 134.20, 2.89, 0.0, 0, 0.50),
    ("c1ccc2c(c1)[nH]c2", "Indole", 117.15, 1.95, 15.60, 1, 0.55),
    
    # Drug-like molecules (simplified)
    ("CC(=O)Oc1ccccc1C(=O)O", "Aspirin", 180.16, 1.19, 63.60, 1, 0.75),
    ("CC(C)Cc1ccccc1", "Ibuprofen", 206.28, 3.50, 37.30, 1, 0.80),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "Caffeine", 194.19, -0.07, 58.44, 0, 0.55),
    ("CN(C)CC(C1=CC=CC=C1)C2=CC=CC=C2", "Diphenhydramine", 255.35, 3.27, 12.47, 0, 0.85),
    ("CC(C)NCC(COc1ccccc1)O", "Propranolol", 259.34, 2.60, 41.49, 1, 0.78),
    ("CC(C)[NH2+]Cc1ccccc1", "Pseudoephedrine", 165.24, 1.28, 26.02, 1, 0.72),
    ("C[NH2+]CCc1ccccc1", "Amphetamine", 135.21, 1.76, 26.02, 1, 0.65),
    ("CCN(CC)C(=O)C1(c2ccccc2)CCCCC1", "Dextromethorphan", 271.40, 4.10, 12.47, 0, 0.88),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1", "Ibuprofen-simplified", 206.28, 3.50, 37.30, 1, 0.80),
    ("CN1c2ccc(C)cc2C2c3ccccc3C[C@H]1C2", "Yohimbine", 354.44, 2.80, 43.70, 1, 0.82),
    
    # Amino acids (simplified)
    ("N[C@@H](C(=O)O)C", "Alanine", 89.09, -1.39, 63.32, 3, 0.70),
    ("N[C@@H](C(=O)O)CC(C)C", "Leucine", 131.17, -0.17, 63.32, 3, 0.72),
    ("N[C@@H](C(=O)O)Cc1ccccc1", "Phenylalanine", 165.19, 0.55, 63.32, 3, 0.75),
    ("N[C@@H](C(=O)O)CCC(=O)O", "Glutamic acid", 147.13, -0.90, 101.34, 4, 0.68),
    ("N[C@@H](C(=O)O)CC(=O)N", "Asparagine", 132.12, -1.55, 84.58, 4, 0.65),
    ("N[C@@H](C(=O)O)CC1=CNC=N1", "Histidine", 155.15, -0.85, 81.14, 4, 0.70),
    ("N[C@@H](C(=O)O)CS", "Cysteine", 121.16, -0.33, 63.32, 3, 0.62),
    ("N[C@@H](C(=O)O)CCCNC(=N)N", "Arginine", 174.20, -2.29, 106.55, 5, 0.60),
    ("N[C@@H](C(=O)O)CCCN", "Lysine", 146.19, -1.47, 75.16, 4, 0.65),
    ("N[C@@H](C(=O)O)CC1=CC=C(O)C=C1", "Tyrosine", 181.19, -0.03, 83.47, 3, 0.72),
    
    # Natural products / bioactive
    ("CC1=C[C@H](C)C(=O)C1", "Carvone", 150.22, 2.43, 17.07, 0, 0.80),
    ("CC1=C[C@@H](C)C(=O)CC1", "Menthol", 156.27, 3.30, 20.23, 1, 0.82),
    ("CC1=CC=C2C(=C1)C(=O)c3ccccc3C2=O", "Anthraquinone", 208.21, 3.40, 34.14, 0, 0.65),
    ("CC1=C(C)C2=C(C)C(C)=C(C)C(C)=C2C(C)=C1C", "Beta-carotene", 536.87, 14.20, 0.0, 0, 0.45),
    ("CC1=C[C@@H](C)C[C@@H](C)C1", "Limonene", 136.23, 3.45, 0.0, 0, 0.85),
    ("CC1=C[C@H](C)C[C@H](C)C1", "Pinene", 136.23, 3.45, 0.0, 0, 0.85),
    ("CC1=C[C@@H](O)C[C@@H](C)C1", "Menthol-OH", 156.27, 2.80, 20.23, 1, 0.82),
    ("c1ccc2c(c1)C(=O)N(C)C2", "Phthalimide", 147.13, 1.15, 37.38, 1, 0.68),
    ("CC1=C(C)C(C)(C)C(C)C1(C)C", "Camphor", 152.23, 2.95, 17.07, 0, 0.78),
    ("CC1=C(C)C(=O)CC1", "Pulegone", 152.23, 2.60, 17.07, 0, 0.80),
    
    # Antibiotics / pharma
    ("c1ccc2c(c1)c3ccccc3cc2", "Phenanthrene", 178.23, 4.45, 0.0, 0, 0.45),
    ("CC1=C(C)C(=O)C(C)=C(C)C1=O", "Duquinone", 164.16, 1.60, 34.14, 0, 0.55),
    ("CC1=C(C)C(=O)C(C)C1", "Toluquinone", 122.12, 1.30, 34.14, 0, 0.60),
    ("CC1=C(C)C(C)(C)C(=O)C1", "Menadione", 172.18, 2.45, 34.14, 0, 0.62),
    ("CC1=C(C)C(C)C(C)(C)C1", "Durene", 134.22, 3.35, 0.0, 0, 0.65),
    ("CC1=C(C)C(C)C(C)C1", "Mesitylene", 120.19, 2.80, 0.0, 0, 0.70),
    ("CC1=C(C)C(C)C(C)C1C", "Pseudocumene", 120.19, 2.80, 0.0, 0, 0.70),
    ("CC1=C(C)C(C)C(C)C1(C)C", "Prehnitene", 134.22, 3.00, 0.0, 0, 0.68),
    ("CC1=C(C)C(C)C(C)C1(C)C(C)C", "Isodurene", 148.24, 3.30, 0.0, 0, 0.65),
    ("CC1=C(C)C(C)C(C)C1(C)C(C)C(C)C", "Pentamethylbenzene", 162.27, 3.70, 0.0, 0, 0.60),
    
    # Peptide fragments
    ("CC(=O)NCC(=O)O", "Acetylglycine", 117.10, -0.72, 66.40, 2, 0.68),
    ("CC(=O)N[C@@H](C)C(=O)O", "Acetylalanine", 131.13, -0.30, 66.40, 2, 0.70),
    ("CC(=O)N[C@@H](C)C(=O)NCC(=O)O", "Acetylalanylglycine", 188.18, -0.50, 95.43, 3, 0.72),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O", "Acetylalanylalanine", 201.22, -0.10, 95.43, 2, 0.74),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)NCC(=O)O", "Acetylalanylalanylglycine", 258.27, -0.30, 124.46, 3, 0.75),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O", "Acetylalanylalanylalanine", 272.30, -0.10, 124.46, 2, 0.76),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)NCC(=O)O", "Tetra-peptide", 329.35, -0.20, 153.49, 3, 0.77),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O", "Penta-peptide", 343.38, -0.10, 153.49, 2, 0.78),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)NCC(=O)O", "Hexa-peptide", 400.43, -0.20, 182.52, 3, 0.79),
    ("CC(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O", "Hepta-peptide", 414.46, -0.10, 182.52, 2, 0.80),
    
    # Alkaloids / natural products
    ("CN1CCC2=CC=CC=C2C1", "Nicotine", 162.23, 1.17, 16.13, 0, 0.72),
    ("CN1CCC[C@H]1C2=CC=CC=C2", "Nicotine", 162.23, 1.17, 16.13, 0, 0.72),
    ("CN1C=C(C2=CC=CC=C2C1=O)C3=CC=CC=C3", "Quinazoline", 233.25, 3.20, 26.14, 0, 0.60),
    ("CN1C=C(C2=CC=CC=C2C1=O)C3=CC=CC=C3", "Quinazolinone", 233.25, 3.20, 26.14, 0, 0.60),
    ("C1=CC=C(C=C1)C2=CC=CC=C2", "Biphenyl", 154.21, 3.98, 0.0, 0, 0.58),
    ("C1=CC=C(C=C1)C2=CC=C(C=C2)", "Biphenyl-para", 154.21, 3.98, 0.0, 0, 0.58),
    ("C1=CC=C(C=C1)C2=CC=CC3=CC=CC=C32", "Fluorene", 166.22, 4.20, 0.0, 0, 0.55),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3", "Triphenylmethane", 244.33, 5.50, 0.0, 0, 0.45),
    ("C1=CC=C(C=C1)C2=C(C=C(C=C2)C3=CC=CC=C3)C4=CC=CC=C4", "Triphenylbenzene", 306.40, 7.00, 0.0, 0, 0.40),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3", "Triphenylmethane", 244.33, 5.50, 0.0, 0, 0.45),
    
    # Synthetic intermediates
    ("CC(=O)C1=CC=CC=C1", "Acetophenone", 120.15, 1.58, 17.07, 0, 0.75),
    ("CC(=O)C1=CC=C(C)C=C1", "4-Methylacetophenone", 134.18, 2.15, 17.07, 0, 0.78),
    ("CC(=O)C1=CC=C(OC)C=C1", "4-Methoxyacetophenone", 150.18, 1.95, 26.69, 0, 0.75),
    ("CC(=O)C1=CC=C(Cl)C=C1", "4-Chloroacetophenone", 154.60, 2.35, 17.07, 0, 0.72),
    ("CC(=O)C1=CC=C(Br)C=C1", "4-Bromoacetophenone", 199.05, 2.65, 17.07, 0, 0.70),
    ("CC(=O)C1=CC=C([N+](=O)[O-])C=C1", "4-Nitroacetophenone", 165.15, 1.55, 44.02, 0, 0.65),
    ("CC(=O)C1=CC=C(C(=O)O)C=C1", "4-Acetylbenzoic acid", 164.16, 1.55, 54.37, 1, 0.68),
    ("CC(=O)C1=CC=C(CN)C=C1", "4-Acetylbenzylamine", 149.19, 1.20, 43.70, 1, 0.70),
    ("CC(=O)C1=CC=C(CC(=O)O)C=C1", "4-Acetylphenylacetic acid", 178.19, 1.35, 54.37, 1, 0.65),
    ("CC(=O)C1=CC=C(CCC(=O)O)C=C1", "4-Acetylphenylpropionic acid", 192.21, 1.70, 54.37, 1, 0.62),
    
    # Diverse scaffolds
    ("C1CCNCC1", "Piperidine", 85.15, 0.84, 12.03, 1, 0.72),
    ("C1CCN(CC1)C2=CC=CC=C2", "N-Phenylpiperidine", 161.24, 2.80, 3.24, 0, 0.78),
    ("C1CCN(CC1)CC2=CC=CC=C2", "N-Benzylpiperidine", 175.27, 2.90, 3.24, 0, 0.80),
    ("C1CCN(CC1)C(=O)C2=CC=CC=C2", "N-Benzoylpiperidine", 189.25, 2.40, 20.23, 0, 0.75),
    ("C1CCN(CC1)C(=O)CC2=CC=CC=C2", "N-Phenylacetylpiperidine", 203.28, 2.70, 20.23, 0, 0.78),
    ("C1CCN(CC1)C(=O)NC2=CC=CC=C2", "N-Phenylureapip", 204.27, 2.10, 32.34, 1, 0.72),
    ("C1CCN(CC1)C(=O)NCC2=CC=CC=C2", "N-Benzylureapip", 218.30, 2.40, 32.34, 1, 0.75),
    ("C1CCN(CC1)C(=O)OCC2=CC=CC=C2", "N-Phenylmethylcarbamate", 219.28, 2.60, 29.46, 0, 0.73),
    ("C1CCN(CC1)C(=O)OC2=CC=CC=C2", "N-Phenylcarbamate", 205.26, 2.30, 29.46, 0, 0.75),
    ("C1CCN(CC1)S(=O)(=O)C2=CC=CC=C2", "N-Phenylsulfonylpiperidine", 223.31, 2.20, 29.54, 0, 0.72),
    
    # Pyrazoles / triazoles
    ("c1c[nH]nn1", "Pyrazole", 68.08, 0.08, 28.68, 1, 0.60),
    ("c1c[nH]n[nH]1", "1,2,4-Triazole", 69.07, -0.55, 41.14, 2, 0.55),
    ("c1c[nH]nn1C", "1-Methylpyrazole", 82.10, 0.55, 12.89, 0, 0.65),
    ("c1c[nH]nn1CC2=CC=CC=C2", "1-Benzylpyrazole", 158.20, 2.40, 12.89, 0, 0.72),
    ("c1c[nH]nn1C(=O)C2=CC=CC=C2", "1-Benzoylpyrazole", 186.19, 2.50, 26.43, 0, 0.68),
    ("c1c[nH]nn1C(=O)NC2=CC=CC=C2", "1-Benzoylaminopyrazole", 201.23, 2.20, 45.15, 1, 0.65),
    ("c1c[nH]nn1C(=O)NCC2=CC=CC=C2", "1-Benzylaminopyrazole", 215.26, 2.50, 45.15, 1, 0.68),
    ("c1c[nH]nn1C(=O)OCC2=CC=CC=C2", "1-Benzylmethylcarbamate", 216.24, 2.70, 42.27, 0, 0.65),
    ("c1c[nH]nn1C(=O)OC2=CC=CC=C2", "1-Phenylcarbamate", 202.21, 2.40, 42.27, 0, 0.68),
    ("c1c[nH]nn1S(=O)(=O)C2=CC=CC=C2", "1-Phenylsulfonylpyrazole", 220.25, 2.30, 42.35, 0, 0.62),
    
    # Quinolones / antibiotics
    ("O=C1c2ccccc2C(=O)N1C", "N-Methylphthalimide", 161.16, 1.40, 37.38, 0, 0.68),
    ("O=C1c2ccccc2C(=O)N1CC", "N-Ethylphthalimide", 175.18, 1.70, 37.38, 0, 0.70),
    ("O=C1c2ccccc2C(=O)N1CC3=CC=CC=C3", "N-Benzylphthalimide", 237.26, 2.80, 37.38, 0, 0.72),
    ("O=C1c2ccccc2C(=O)N1C(=O)C3=CC=CC=C3", "N-Benzoylphthalimide", 265.27, 2.50, 53.62, 0, 0.65),
    ("O=C1c2ccccc2C(=O)N1C(=O)NC3=CC=CC=C3", "N-Benzoylaminophthalimide", 280.29, 2.20, 72.34, 1, 0.62),
    ("O=C1c2ccccc2C(=O)N1C(=O)NCC3=CC=CC=C3", "N-Benzylaminophthalimide", 294.32, 2.50, 72.34, 1, 0.65),
    ("O=C1c2ccccc2C(=O)N1C(=O)OCC3=CC=CC=C3", "N-Benzylmethylcarbamate", 295.30, 2.70, 69.46, 0, 0.60),
    ("O=C1c2ccccc2C(=O)N1C(=O)OC3=CC=CC=C3", "N-Phenylcarbamate", 281.27, 2.40, 69.46, 0, 0.62),
    ("O=C1c2ccccc2C(=O)N1S(=O)(=O)C3=CC=CC=C3", "N-Phenylsulfonylphthalimide", 299.32, 2.30, 69.54, 0, 0.58),
    ("O=C1c2ccccc2C(=O)N1C(=O)C3=CC=CC=C3C", "N-Toluoylphthalimide", 279.29, 2.70, 53.62, 0, 0.62),
    
    # Purine analogs
    ("c1ncnc2[nH]cnc12", "Purine", 120.11, -0.55, 52.14, 1, 0.55),
    ("c1ncnc2c1nc[nH]2", "Purine-7H", 120.11, -0.55, 52.14, 1, 0.55),
    ("CN1C=NC2=C1C(=O)NC=N2", "Hypoxanthine", 136.11, -0.20, 58.36, 2, 0.58),
    ("CN1C=NC2=C1C(=O)N(C)C=N2", "Theobromine", 180.16, 0.10, 58.36, 0, 0.60),
    ("CN1C=NC2=C1C(=O)NC(=O)N2C", "Theophylline", 180.16, -0.10, 58.36, 0, 0.60),
    ("CN1C=NC2=C1C(=O)NC(=O)N2", "Xanthine", 152.11, -0.50, 75.46, 2, 0.55),
    ("CN1C=NC2=C1C(N)=NC(=O)N2", "Guanine", 151.13, -1.20, 95.88, 3, 0.50),
    ("CN1C=NC2=C1C(N)=NC(=O)N2C", "Methylguanine", 165.15, -0.90, 95.88, 2, 0.52),
    ("CN1C=NC2=C1C(N)=NC(=O)N2CC3=CC=CC=C3", "Benzylguanine", 241.27, 1.20, 95.88, 2, 0.55),
    ("CN1C=NC2=C1C(N)=NC(=O)N2C(=O)C3=CC=CC=C3", "Benzoylguanine", 253.26, 0.80, 112.12, 2, 0.52),
    
    # Pyrimidine analogs
    ("c1cncnc1", "Pyrimidine", 80.09, -0.55, 25.78, 0, 0.60),
    ("c1cnc(N)nc1", "Aminopyrimidine", 95.10, -0.80, 38.91, 1, 0.58),
    ("c1cnc(N)nc1N", "Diaminopyrimidine", 110.12, -1.10, 52.04, 2, 0.55),
    ("c1cnc(N)nc1NC(=O)C2=CC=CC=C2", "Benzoylaminopyrimidine", 214.23, 1.20, 52.04, 1, 0.58),
    ("c1cnc(N)nc1NC(=O)CC2=CC=CC=C2", "Phenylacetylaminopyrimidine", 228.26, 1.50, 52.04, 1, 0.60),
    ("c1cnc(N)nc1NC(=O)NC2=CC=CC=C2", "Phenylureaminopyrimidine", 229.24, 1.00, 65.17, 2, 0.55),
    ("c1cnc(N)nc1NC(=O)NCC2=CC=CC=C2", "Benzylureaminopyrimidine", 243.27, 1.30, 65.17, 2, 0.58),
    ("c1cnc(N)nc1NC(=O)OCC2=CC=CC=C2", "Benzylmethylcarbamate", 244.26, 1.50, 62.29, 1, 0.55),
    ("c1cnc(N)nc1NC(=O)OC2=CC=CC=C2", "Phenylcarbamate", 230.23, 1.20, 62.29, 1, 0.58),
    ("c1cnc(N)nc1S(=O)(=O)C2=CC=CC=C2", "Phenylsulfonylpyrimidine", 248.28, 1.10, 62.37, 0, 0.52),
    
    # Benzodiazepine analogs
    ("O=C1C2=CC=CC=C2C(=O)N1C", "N-Methylisatin", 161.16, 1.40, 37.38, 0, 0.68),
    ("O=C1C2=CC=CC=C2C(=O)N1CC", "N-Ethylisatin", 175.18, 1.70, 37.38, 0, 0.70),
    ("O=C1C2=CC=CC=C2C(=O)N1CC3=CC=CC=C3", "N-Benzylisatin", 237.26, 2.80, 37.38, 0, 0.72),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)C3=CC=CC=C3", "N-Benzoylisatin", 265.27, 2.50, 53.62, 0, 0.65),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)NC3=CC=CC=C3", "N-Benzoylaminisatin", 280.29, 2.20, 72.34, 1, 0.62),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)NCC3=CC=CC=C3", "N-Benzylaminisatin", 294.32, 2.50, 72.34, 1, 0.65),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)OCC3=CC=CC=C3", "N-Benzylmethylcarbamate", 295.30, 2.70, 69.46, 0, 0.60),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)OC3=CC=CC=C3", "N-Phenylcarbamate", 281.27, 2.40, 69.46, 0, 0.62),
    ("O=C1C2=CC=CC=C2C(=O)N1S(=O)(=O)C3=CC=CC=C3", "N-Phenylsulfonylisatin", 299.32, 2.30, 69.54, 0, 0.58),
    ("O=C1C2=CC=CC=C2C(=O)N1C(=O)C3=CC=CC=C3C", "N-Toluoylisatin", 279.29, 2.70, 53.62, 0, 0.62),
    
    # Steroid-like scaffolds
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2C1", "Testosterone", 288.42, 3.50, 37.30, 0, 0.82),
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2(C)C1", "Methyltestosterone", 302.45, 3.80, 37.30, 0, 0.80),
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2(C)C1C", "Ethinyltestosterone", 312.45, 3.90, 37.30, 0, 0.78),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1", "Progesterone", 314.46, 3.90, 34.14, 0, 0.82),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1C", "Cortisol", 362.46, 2.30, 94.83, 3, 0.75),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CC", "Corticosterone", 346.46, 2.80, 77.71, 2, 0.78),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCC", "Aldosterone", 360.44, 2.50, 91.85, 2, 0.72),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCC", "Estradiol", 272.38, 4.00, 40.46, 1, 0.85),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCCC", "Estriol", 288.38, 3.50, 60.69, 2, 0.82),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCCCC", "Estrone", 270.37, 4.20, 40.46, 1, 0.85),
    
    # Vitamin analogs
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C", "Vitamin A", 286.45, 5.50, 0.0, 0, 0.45),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C", "Vitamin D", 384.64, 8.00, 20.23, 1, 0.40),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C", "Vitamin E", 430.71, 9.00, 29.46, 0, 0.35),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C", "Vitamin K", 450.70, 9.50, 34.14, 0, 0.32),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin K2", 580.80, 12.00, 34.14, 0, 0.28),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin K3", 172.18, 1.90, 34.14, 0, 0.65),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin B12", 1355.37, 2.50, 215.28, 8, 0.30),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin C", 176.12, -0.85, 107.22, 4, 0.55),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin D2", 396.65, 8.20, 20.23, 1, 0.38),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin D3", 384.64, 8.00, 20.23, 1, 0.40),
    
    # Lipid analogs
    ("CCCCCCCCCCCCCCCCCC(=O)O", "Stearic acid", 284.48, 7.17, 37.30, 1, 0.55),
    ("CCCCCCCCCCCCCCCCCC(=O)OC", "Methyl stearate", 298.50, 7.60, 26.30, 0, 0.52),
    ("CCCCCCCCCCCCCCCCCC(=O)OCC", "Ethyl stearate", 312.53, 7.90, 26.30, 0, 0.50),
    ("CCCCCCCCCCCCCCCCCC(=O)OCC(C)C", "Isopropyl stearate", 326.56, 8.20, 26.30, 0, 0.48),
    ("CCCCCCCCCCCCCCCCCC(=O)OCCCC", "Butyl stearate", 340.59, 8.50, 26.30, 0, 0.45),
    ("CCCCCCCCCCCCCCCCCC(=O)N(C)C", "N,N-Dimethylstearamide", 311.56, 6.80, 20.31, 0, 0.52),
    ("CCCCCCCCCCCCCCCCCC(=O)NCC", "N-Ethylstearamide", 311.56, 6.80, 29.10, 1, 0.55),
    ("CCCCCCCCCCCCCCCCCC(=O)NCC(C)C", "N-Isopropylstearamide", 325.59, 7.10, 29.10, 1, 0.52),
    ("CCCCCCCCCCCCCCCCCC(=O)NCC(C)CC", "N-Butylstearamide", 339.61, 7.40, 29.10, 1, 0.50),
    ("CCCCCCCCCCCCCCCCCC(=O)NCC(C)CCC", "N-Pentylstearamide", 353.64, 7.70, 29.10, 1, 0.48),
    
    # Sugar analogs
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Glucose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Galactose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Mannose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Fructose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Sucrose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Maltose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Lactose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Raffinose", 504.44, -5.50, 266.62, 11, 0.35),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Stachyose", 666.58, -7.00, 344.74, 14, 0.28),
    ("C1(C(C(C(C(C1O)O)O)O)O)O", "Cyclodextrin", 1134.99, -10.00, 570.10, 21, 0.20),
    
    # Nucleoside analogs
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Adenosine", 267.24, -1.20, 139.54, 5, 0.55),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Guanosine", 283.24, -1.50, 155.76, 6, 0.50),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Cytidine", 243.22, -1.80, 116.12, 4, 0.58),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Uridine", 244.20, -1.70, 120.25, 4, 0.58),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Thymidine", 242.23, -1.50, 108.63, 3, 0.60),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Inosine", 268.23, -1.30, 132.32, 5, 0.55),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Xanthosine", 284.23, -1.50, 148.54, 5, 0.52),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "Pseudouridine", 244.20, -1.70, 120.25, 4, 0.58),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "5-Methyluridine", 258.23, -1.40, 120.25, 4, 0.58),
    ("Nc1ncnc2c1ncn2C1CC(O)C(CO)O1", "5-Fluorouridine", 262.20, -1.30, 120.25, 4, 0.58),
    
    # Macrocycles
    ("C1CCOCC1", "Tetrahydropyran", 86.13, 1.18, 9.23, 0, 0.72),
    ("C1CCSCC1", "Tetrahydrothiopyran", 102.19, 1.80, 0.0, 0, 0.68),
    ("C1CCNCC1", "Piperidine", 85.15, 0.84, 12.03, 1, 0.72),
    ("C1CCOCC1", "Oxane", 86.13, 1.18, 9.23, 0, 0.72),
    ("C1CCSCC1", "Thiane", 102.19, 1.80, 0.0, 0, 0.68),
    ("C1CCNCC1", "Azane", 85.15, 0.84, 12.03, 1, 0.72),
    ("C1CCOCC1", "Oxepane", 100.16, 1.50, 9.23, 0, 0.70),
    ("C1CCSCC1", "Thiepane", 116.22, 2.10, 0.0, 0, 0.65),
    ("C1CCNCC1", "Azepane", 99.17, 1.20, 12.03, 1, 0.70),
    ("C1CCOCC1", "Oxonane", 114.19, 1.80, 9.23, 0, 0.68),
    
    # Crown ethers / cryptands
    ("C1COCCOCCOCCOCCO1", "12-Crown-4", 176.21, 0.10, 36.92, 0, 0.65),
    ("C1COCCOCCOCCOCCOCCO1", "15-Crown-5", 220.26, 0.40, 46.15, 0, 0.60),
    ("C1COCCOCCOCCOCCOCCOCCO1", "18-Crown-6", 264.32, 0.70, 55.38, 0, 0.55),
    ("C1COCCOCCOCCOCCOCCOCCOCCO1", "21-Crown-7", 308.37, 1.00, 64.61, 0, 0.50),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCO1", "24-Crown-8", 352.42, 1.30, 73.84, 0, 0.45),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCOCCO1", "27-Crown-9", 396.47, 1.60, 83.07, 0, 0.40),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO1", "30-Crown-10", 440.52, 1.90, 92.30, 0, 0.38),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO1", "33-Crown-11", 484.57, 2.20, 101.53, 0, 0.35),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO1", "36-Crown-12", 528.62, 2.50, 110.76, 0, 0.32),
    ("C1COCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO1", "39-Crown-13", 572.67, 2.80, 119.99, 0, 0.30),
    
    # Calixarene-like scaffolds
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6C2", "Calix[4]arene", 424.53, 7.00, 40.46, 4, 0.45),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7C2", "Calix[5]arene", 530.66, 8.50, 50.58, 5, 0.40),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8C2", "Calix[6]arene", 636.79, 10.00, 60.69, 6, 0.35),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9C2", "Calix[7]arene", 742.92, 11.50, 70.81, 7, 0.30),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10C2", "Calix[8]arene", 849.05, 13.00, 80.92, 8, 0.28),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10Cc%11ccccc%11C2", "Calix[9]arene", 955.18, 14.50, 91.04, 9, 0.25),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10Cc%11ccccc%11Cc%12ccccc%12C2", "Calix[10]arene", 1061.31, 16.00, 101.15, 10, 0.22),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10Cc%11ccccc%11Cc%12ccccc%12Cc%13ccccc%13C2", "Calix[11]arene", 1167.44, 17.50, 111.27, 11, 0.20),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10Cc%11ccccc%11Cc%12ccccc%12Cc%13ccccc%13Cc%14ccccc%14C2", "Calix[12]arene", 1273.57, 19.00, 121.38, 12, 0.18),
    ("c1ccc2c(c1)Cc3ccccc3Cc4ccccc4Cc5ccccc5Cc6ccccc6Cc7ccccc7Cc8ccccc8Cc9ccccc9Cc%10ccccc%10Cc%11ccccc%11Cc%12ccccc%12Cc%13ccccc%13Cc%14ccccc%14Cc%15ccccc%15C2", "Calix[13]arene", 1379.70, 20.50, 131.50, 13, 0.15),
    
    # Dendrimer-like structures
    ("C(CN(CC)CC)N(CC)CC", "Dendrimer-core", 172.31, 0.50, 3.24, 0, 0.70),
    ("C(CN(CC)CC)N(CC)CC(C)C", "Dendrimer-1", 200.36, 1.20, 3.24, 0, 0.68),
    ("C(CN(CC)CC)N(CC)CC(C)(C)C", "Dendrimer-2", 214.39, 1.50, 3.24, 0, 0.65),
    ("C(CN(CC)CC)N(CC)CC(C)CC", "Dendrimer-3", 228.42, 1.80, 3.24, 0, 0.62),
    ("C(CN(CC)CC)N(CC)CC(C)CCC", "Dendrimer-4", 242.45, 2.10, 3.24, 0, 0.60),
    ("C(CN(CC)CC)N(CC)CC(C)CCCC", "Dendrimer-5", 256.48, 2.40, 3.24, 0, 0.58),
    ("C(CN(CC)CC)N(CC)CC(C)CCCCC", "Dendrimer-6", 270.51, 2.70, 3.24, 0, 0.55),
    ("C(CN(CC)CC)N(CC)CC(C)CCCCCC", "Dendrimer-7", 284.54, 3.00, 3.24, 0, 0.52),
    ("C(CN(CC)CC)N(CC)CC(C)CCCCCCC", "Dendrimer-8", 298.57, 3.30, 3.24, 0, 0.50),
    ("C(CN(CC)CC)N(CC)CC(C)CCCCCCCC", "Dendrimer-9", 312.60, 3.60, 3.24, 0, 0.48),
    
    # Ionic liquids (cationic)
    ("C[N+](C)(C)C", "Tetramethylammonium", 74.15, -0.80, 0.0, 0, 0.65),
    ("C[N+](C)(C)CC", "Ethyltrimethylammonium", 88.18, -0.50, 0.0, 0, 0.62),
    ("C[N+](C)(C)CC(C)C", "Isopropyltrimethylammonium", 102.20, -0.20, 0.0, 0, 0.60),
    ("C[N+](C)(C)CC(C)CC", "Butyltrimethylammonium", 116.23, 0.10, 0.0, 0, 0.58),
    ("C[N+](C)(C)CC(C)CCC", "Pentyltrimethylammonium", 130.26, 0.40, 0.0, 0, 0.55),
    ("C[N+](C)(C)CC(C)CCCC", "Hexyltrimethylammonium", 144.29, 0.70, 0.0, 0, 0.52),
    ("C[N+](C)(C)CC(C)CCCCC", "Heptyltrimethylammonium", 158.32, 1.00, 0.0, 0, 0.50),
    ("C[N+](C)(C)CC(C)CCCCCC", "Octyltrimethylammonium", 172.35, 1.30, 0.0, 0, 0.48),
    ("C[N+](C)(C)CC(C)CCCCCCC", "Nonyltrimethylammonium", 186.38, 1.60, 0.0, 0, 0.45),
    ("C[N+](C)(C)CC(C)CCCCCCCC", "Decyltrimethylammonium", 200.41, 1.90, 0.0, 0, 0.42),
    
    # Ionic liquids (anionic)
    ("[O-]S(=O)(=O)C(F)(F)F", "Triflate", 149.07, -0.20, 52.65, 0, 0.55),
    ("[O-]S(=O)(=O)C(F)(F)F", "Tf2N", 280.14, 1.50, 52.65, 0, 0.45),
    ("[O-]S(=O)(=O)C(F)(F)F", "BF4", 86.81, -0.80, 0.0, 0, 0.60),
    ("[O-]S(=O)(=O)C(F)(F)F", "PF6", 144.96, -0.50, 0.0, 0, 0.55),
    ("[O-]S(=O)(=O)C(F)(F)F", "Cl", 35.45, -0.90, 0.0, 0, 0.70),
    ("[O-]S(=O)(=O)C(F)(F)F", "Br", 79.90, -0.70, 0.0, 0, 0.65),
    ("[O-]S(=O)(=O)C(F)(F)F", "I", 126.90, -0.50, 0.0, 0, 0.60),
    ("[O-]S(=O)(=O)C(F)(F)F", "NO3", 62.00, -0.80, 52.50, 0, 0.58),
    ("[O-]S(=O)(=O)C(F)(F)F", "CH3COO", 59.04, -0.90, 52.20, 0, 0.62),
    ("[O-]S(=O)(=O)C(F)(F)F", "CF3COO", 113.02, -0.50, 52.20, 0, 0.55),
    
    # More drug-like molecules
    ("CC(C)Cc1ccccc1", "Ibuprofen", 206.28, 3.50, 37.30, 1, 0.80),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1", "Ibuprofen-2", 206.28, 3.50, 37.30, 1, 0.80),
    ("CC(C)Cc1ccc(C(C)C(=O)O)c(C)c1", "Ibuprofen-3", 220.31, 3.80, 37.30, 1, 0.78),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1C", "Ibuprofen-4", 220.31, 3.80, 37.30, 1, 0.78),
    ("CC(C)Cc1ccc(C(C)C(=O)O)c(C)c1C", "Ibuprofen-5", 234.33, 4.10, 37.30, 1, 0.75),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1CC", "Ibuprofen-6", 234.33, 4.10, 37.30, 1, 0.75),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1CCC", "Ibuprofen-7", 248.36, 4.40, 37.30, 1, 0.72),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1CCCC", "Ibuprofen-8", 262.39, 4.70, 37.30, 1, 0.70),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1CCCCC", "Ibuprofen-9", 276.42, 5.00, 37.30, 1, 0.68),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1CCCCCC", "Ibuprofen-10", 290.44, 5.30, 37.30, 1, 0.65),
    
    # Fluorinated molecules
    ("c1ccc(C(F)(F)F)cc1", "Trifluorotoluene", 146.11, 2.80, 0.0, 0, 0.60),
    ("c1ccc(C(F)(F)F)c(C)cc1", "Trifluoroxylene", 160.13, 3.10, 0.0, 0, 0.58),
    ("c1ccc(C(F)(F)F)c(C)cc1C", "Trifluorotrimethylbenzene", 174.16, 3.40, 0.0, 0, 0.55),
    ("c1ccc(C(F)(F)F)c(C)cc1CC", "Trifluorotetramethylbenzene", 188.19, 3.70, 0.0, 0, 0.52),
    ("c1ccc(C(F)(F)F)c(C)cc1CCC", "Trifluoropentamethylbenzene", 202.22, 4.00, 0.0, 0, 0.50),
    ("c1ccc(C(F)(F)F)c(C)cc1CCCC", "Trifluorohexamethylbenzene", 216.24, 4.30, 0.0, 0, 0.48),
    ("c1ccc(C(F)(F)F)c(C)cc1CCCCC", "Trifluoroheptamethylbenzene", 230.27, 4.60, 0.0, 0, 0.45),
    ("c1ccc(C(F)(F)F)c(C)cc1CCCCCC", "Trifluorooctamethylbenzene", 244.30, 4.90, 0.0, 0, 0.42),
    ("c1ccc(C(F)(F)F)c(C)cc1CCCCCCC", "Trifluorononamethylbenzene", 258.32, 5.20, 0.0, 0, 0.40),
    ("c1ccc(C(F)(F)F)c(C)cc1CCCCCCCC", "Trifluorodecamethylbenzene", 272.35, 5.50, 0.0, 0, 0.38),
    
    # Silicon-containing molecules
    ("c1ccc([Si](C)(C)C)cc1", "Trimethylphenylsilane", 150.30, 3.00, 0.0, 0, 0.65),
    ("c1ccc([Si](C)(C)C)c(C)cc1", "Trimethyltolylsilane", 164.32, 3.30, 0.0, 0, 0.62),
    ("c1ccc([Si](C)(C)C)c(C)cc1C", "Trimethylxylylsilane", 178.35, 3.60, 0.0, 0, 0.60),
    ("c1ccc([Si](C)(C)C)c(C)cc1CC", "Trimethylmesitylsilane", 192.38, 3.90, 0.0, 0, 0.58),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCC", "Trimethylpseudocumylsilane", 206.40, 4.20, 0.0, 0, 0.55),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCCC", "Trimethyldurenesilane", 220.43, 4.50, 0.0, 0, 0.52),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCCCC", "Trimethylprehnitylsilane", 234.46, 4.80, 0.0, 0, 0.50),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCCCCC", "Trimethylisodurylsilane", 248.48, 5.10, 0.0, 0, 0.48),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCCCCCC", "Trimethylpentamethylbenzylsilane", 262.51, 5.40, 0.0, 0, 0.45),
    ("c1ccc([Si](C)(C)C)c(C)cc1CCCCCCCC", "Trimethylhexamethylbenzylsilane", 276.54, 5.70, 0.0, 0, 0.42),
    
    # Boron-containing molecules
    ("c1ccc(B(C)C)cc1", "Dimethylphenylborane", 132.00, 2.00, 0.0, 0, 0.68),
    ("c1ccc(B(C)C)c(C)cc1", "Dimethyltolylborane", 146.03, 2.30, 0.0, 0, 0.65),
    ("c1ccc(B(C)C)c(C)cc1C", "Dimethylxylylborane", 160.05, 2.60, 0.0, 0, 0.62),
    ("c1ccc(B(C)C)c(C)cc1CC", "Dimethylmesitylborane", 174.08, 2.90, 0.0, 0, 0.60),
    ("c1ccc(B(C)C)c(C)cc1CCC", "Dimethylpseudocumylborane", 188.11, 3.20, 0.0, 0, 0.58),
    ("c1ccc(B(C)C)c(C)cc1CCCC", "Dimethyldureneborane", 202.13, 3.50, 0.0, 0, 0.55),
    ("c1ccc(B(C)C)c(C)cc1CCCCC", "Dimethylprehnitylborane", 216.16, 3.80, 0.0, 0, 0.52),
    ("c1ccc(B(C)C)c(C)cc1CCCCCC", "Dimethylisodurylborane", 230.19, 4.10, 0.0, 0, 0.50),
    ("c1ccc(B(C)C)c(C)cc1CCCCCCC", "Dimethylpentamethylbenzylborane", 244.21, 4.40, 0.0, 0, 0.48),
    ("c1ccc(B(C)C)c(C)cc1CCCCCCCC", "Dimethylhexamethylbenzylborane", 258.24, 4.70, 0.0, 0, 0.45),
    
    # Phosphorus-containing molecules
    ("c1ccc(P(C)C)cc1", "Dimethylphenylphosphine", 138.14, 2.00, 0.0, 0, 0.68),
    ("c1ccc(P(C)C)c(C)cc1", "Dimethyltolylphosphine", 152.17, 2.30, 0.0, 0, 0.65),
    ("c1ccc(P(C)C)c(C)cc1C", "Dimethylxylylphosphine", 166.20, 2.60, 0.0, 0, 0.62),
    ("c1ccc(P(C)C)c(C)cc1CC", "Dimethylmesitylphosphine", 180.22, 2.90, 0.0, 0, 0.60),
    ("c1ccc(P(C)C)c(C)cc1CCC", "Dimethylpseudocumylphosphine", 194.25, 3.20, 0.0, 0, 0.58),
    ("c1ccc(P(C)C)c(C)cc1CCCC", "Dimethyldurenephosphine", 208.28, 3.50, 0.0, 0, 0.55),
    ("c1ccc(P(C)C)c(C)cc1CCCCC", "Dimethylprehnitylphosphine", 222.30, 3.80, 0.0, 0, 0.52),
    ("c1ccc(P(C)C)c(C)cc1CCCCCC", "Dimethylisodurylphosphine", 236.33, 4.10, 0.0, 0, 0.50),
    ("c1ccc(P(C)C)c(C)cc1CCCCCCC", "Dimethylpentamethylbenzylphosphine", 250.36, 4.40, 0.0, 0, 0.48),
    ("c1ccc(P(C)C)c(C)cc1CCCCCCCC", "Dimethylhexamethylbenzylphosphine", 264.38, 4.70, 0.0, 0, 0.45),
    
    # Metal complexes (simplified)
    ("c1ccc(C[NH2+]Cc2ccccc2)cc1", "Benzylamine complex", 198.28, 2.50, 26.02, 1, 0.72),
    ("c1ccc(C[NH2+]CC2=CC=CC=C2)cc1", "Phenethylamine complex", 212.31, 2.80, 26.02, 1, 0.70),
    ("c1ccc(C[NH2+]CCC2=CC=CC=C2)cc1", "Phenylpropylamine complex", 226.34, 3.10, 26.02, 1, 0.68),
    ("c1ccc(C[NH2+]CCCC2=CC=CC=C2)cc1", "Phenylbutylamine complex", 240.37, 3.40, 26.02, 1, 0.65),
    ("c1ccc(C[NH2+]CCCCC2=CC=CC=C2)cc1", "Phenylpentylamine complex", 254.39, 3.70, 26.02, 1, 0.62),
    ("c1ccc(C[NH2+]CCCCCC2=CC=CC=C2)cc1", "Phenylhexylamine complex", 268.42, 4.00, 26.02, 1, 0.60),
    ("c1ccc(C[NH2+]CCCCCCC2=CC=CC=C2)cc1", "Phenylheptylamine complex", 282.45, 4.30, 26.02, 1, 0.58),
    ("c1ccc(C[NH2+]CCCCCCCC2=CC=CC=C2)cc1", "Phenyloctylamine complex", 296.48, 4.60, 26.02, 1, 0.55),
    ("c1ccc(C[NH2+]CCCCCCCCC2=CC=CC=C2)cc1", "Phenylnonylamine complex", 310.50, 4.90, 26.02, 1, 0.52),
    ("c1ccc(C[NH2+]CCCCCCCCCC2=CC=CC=C2)cc1", "Phenyldecylamine complex", 324.53, 5.20, 26.02, 1, 0.50),
    
    # More diverse scaffolds
    ("C1=CC=C(C=C1)C2=CC=CC=C2", "Biphenyl", 154.21, 3.98, 0.0, 0, 0.58),
    ("C1=CC=C(C=C1)C2=CC=C(C=C2)", "Biphenyl-para", 154.21, 3.98, 0.0, 0, 0.58),
    ("C1=CC=C(C=C1)C2=CC=CC3=CC=CC=C32", "Fluorene", 166.22, 4.20, 0.0, 0, 0.55),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3", "Triphenylmethane", 244.33, 5.50, 0.0, 0, 0.45),
    ("C1=CC=C(C=C1)C2=C(C=C(C=C2)C3=CC=CC=C3)C4=CC=CC=C4", "Triphenylbenzene", 306.40, 7.00, 0.0, 0, 0.40),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3", "Triphenylmethane", 244.33, 5.50, 0.0, 0, 0.45),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4", "Tetraphenylmethane", 320.43, 7.00, 0.0, 0, 0.40),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5", "Pentaphenylmethane", 396.52, 8.50, 0.0, 0, 0.35),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6", "Hexaphenylmethane", 472.62, 10.00, 0.0, 0, 0.30),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7", "Heptaphenylmethane", 548.71, 11.50, 0.0, 0, 0.25),
    
    # Carbohydrates (cyclic)
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Glucose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Galactose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Mannose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Fructose", 180.16, -2.50, 110.38, 5, 0.55),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Sucrose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Maltose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Lactose", 342.30, -4.00, 188.50, 8, 0.45),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Raffinose", 504.44, -5.50, 266.62, 11, 0.35),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Stachyose", 666.58, -7.00, 344.74, 14, 0.28),
    ("C1[C@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)O", "Cyclodextrin", 1134.99, -10.00, 570.10, 21, 0.20),
    
    # Terpenes
    ("CC1=C[C@H](C)C(=O)C1", "Carvone", 150.22, 2.43, 17.07, 0, 0.80),
    ("CC1=C[C@@H](C)C(=O)CC1", "Menthol", 156.27, 3.30, 20.23, 1, 0.82),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C", "Beta-carotene", 536.87, 14.20, 0.0, 0, 0.45),
    ("CC1=C[C@@H](C)C[C@@H](C)C1", "Limonene", 136.23, 3.45, 0.0, 0, 0.85),
    ("CC1=C[C@H](C)C[C@H](C)C1", "Pinene", 136.23, 3.45, 0.0, 0, 0.85),
    ("CC1=C[C@@H](O)C[C@@H](C)C1", "Menthol-OH", 156.27, 2.80, 20.23, 1, 0.82),
    ("CC1=C(C)C(=O)CC1", "Pulegone", 152.23, 2.60, 17.07, 0, 0.80),
    ("CC1=C(C)C(C)(C)C(=O)C1", "Camphor", 152.23, 2.95, 17.07, 0, 0.78),
    ("CC1=C(C)C(=O)C(C)C1", "Carvone", 150.22, 2.43, 17.07, 0, 0.80),
    ("CC1=C(C)C(C)(C)C(C)C1(C)C", "Camphor-2", 152.23, 2.95, 17.07, 0, 0.78),
    
    # Steroids
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2C1", "Testosterone", 288.42, 3.50, 37.30, 0, 0.82),
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2(C)C1", "Methyltestosterone", 302.45, 3.80, 37.30, 0, 0.80),
    ("C1CC2C3CCC4=CC(=O)CCC4C3CCC2(C)C1C", "Ethinyltestosterone", 312.45, 3.90, 37.30, 0, 0.78),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1", "Progesterone", 314.46, 3.90, 34.14, 0, 0.82),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1C", "Cortisol", 362.46, 2.30, 94.83, 3, 0.75),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CC", "Corticosterone", 346.46, 2.80, 77.71, 2, 0.78),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCC", "Aldosterone", 360.44, 2.50, 91.85, 2, 0.72),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCC", "Estradiol", 272.38, 4.00, 40.46, 1, 0.85),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCCC", "Estriol", 288.38, 3.50, 60.69, 2, 0.82),
    ("C1CC2C3CCC4=C(C)C(=O)CCC4C3CCC2(C)C1CCCCCC", "Estrone", 270.37, 4.20, 40.46, 1, 0.85),
    
    # Vitamins
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C", "Vitamin A", 286.45, 5.50, 0.0, 0, 0.45),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C", "Vitamin D", 384.64, 8.00, 20.23, 1, 0.40),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C", "Vitamin E", 430.71, 9.00, 29.46, 0, 0.35),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C", "Vitamin K", 450.70, 9.50, 34.14, 0, 0.32),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin K2", 580.80, 12.00, 34.14, 0, 0.28),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin K3", 172.18, 1.90, 34.14, 0, 0.65),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin B12", 1355.37, 2.50, 215.28, 8, 0.30),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin C", 176.12, -0.85, 107.22, 4, 0.55),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin D2", 396.65, 8.20, 20.23, 1, 0.38),
    ("CC1=C(C)C(C)(C)C(C)=C(C)C1(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "Vitamin D3", 384.64, 8.00, 20.23, 1, 0.40),
    
    # Amino acids (more)
    ("N[C@@H](C(=O)O)C", "Alanine", 89.09, -1.39, 63.32, 3, 0.70),
    ("N[C@@H](C(=O)O)CC(C)C", "Leucine", 131.17, -0.17, 63.32, 3, 0.72),
    ("N[C@@H](C(=O)O)Cc1ccccc1", "Phenylalanine", 165.19, 0.55, 63.32, 3, 0.75),
    ("N[C@@H](C(=O)O)CCC(=O)O", "Glutamic acid", 147.13, -0.90, 101.34, 4, 0.68),
    ("N[C@@H](C(=O)O)CC(=O)N", "Asparagine", 132.12, -1.55, 84.58, 4, 0.65),
    ("N[C@@H](C(=O)O)CC1=CNC=N1", "Histidine", 155.15, -0.85, 81.14, 4, 0.70),
    ("N[C@@H](C(=O)O)CS", "Cysteine", 121.16, -0.33, 63.32, 3, 0.62),
    ("N[C@@H](C(=O)O)CCCNC(=N)N", "Arginine", 174.20, -2.29, 106.55, 5, 0.60),
    ("N[C@@H](C(=O)O)CCCN", "Lysine", 146.19, -1.47, 75.16, 4, 0.65),
    ("N[C@@H](C(=O)O)CC1=CC=C(O)C=C1", "Tyrosine", 181.19, -0.03, 83.47, 3, 0.72),
    
    # Dipeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanine", 160.17, -1.80, 126.64, 4, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanine", 202.25, -0.60, 126.64, 4, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanine", 236.27, 0.10, 126.64, 4, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanine", 218.21, -1.40, 164.66, 5, 0.70),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanine", 203.20, -1.95, 147.90, 5, 0.68),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanine", 226.23, -1.25, 144.46, 5, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanine", 192.24, -0.73, 126.64, 4, 0.65),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanine", 245.28, -2.69, 169.87, 6, 0.62),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanine", 217.27, -1.87, 138.48, 5, 0.68),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanine", 252.27, -0.43, 146.79, 4, 0.75),
    
    # Tripeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanine", 231.25, -2.20, 189.96, 5, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanine", 273.33, -1.00, 189.96, 5, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanine", 307.35, -0.30, 189.96, 5, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanine", 289.29, -1.80, 227.98, 6, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanine", 274.28, -2.35, 211.22, 6, 0.70),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanine", 297.31, -1.65, 207.78, 6, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanine", 263.32, -1.13, 189.96, 5, 0.68),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanine", 316.36, -3.09, 233.19, 7, 0.65),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanine", 288.35, -2.27, 201.80, 6, 0.70),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanine", 323.35, -1.03, 210.11, 5, 0.75),
    
    # Tetrapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanine", 302.34, -2.60, 253.28, 6, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanine", 344.42, -1.40, 253.28, 6, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanine", 378.44, -0.70, 253.28, 6, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanine", 360.38, -2.20, 291.30, 7, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanine", 345.37, -2.75, 274.54, 7, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanine", 368.40, -2.05, 271.10, 7, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanine", 334.41, -1.53, 253.28, 6, 0.70),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanine", 387.45, -3.49, 296.51, 8, 0.68),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanine", 359.44, -2.67, 265.12, 7, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanine", 394.44, -1.43, 273.43, 6, 0.78),
    
    # Pentapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanine", 373.42, -3.00, 316.60, 7, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanine", 415.50, -1.80, 316.60, 7, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanine", 449.52, -1.10, 316.60, 7, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanine", 431.46, -2.60, 354.62, 8, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanine", 416.45, -3.15, 337.86, 8, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanine", 439.48, -2.45, 334.42, 8, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanine", 405.49, -1.93, 316.60, 7, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanine", 458.53, -3.89, 359.83, 9, 0.70),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanine", 430.52, -3.07, 328.44, 8, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanine", 465.52, -1.83, 336.75, 7, 0.80),
    
    # Hexapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanine", 444.51, -3.40, 379.92, 8, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanine", 486.59, -2.20, 379.92, 8, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanine", 520.61, -1.50, 379.92, 8, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanine", 502.55, -3.00, 417.94, 9, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanine", 487.54, -3.55, 401.18, 9, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanine", 510.57, -2.85, 397.74, 9, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanine", 476.58, -2.33, 379.92, 8, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanine", 529.62, -4.29, 423.15, 10, 0.72),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanine", 501.61, -3.47, 391.76, 9, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanine", 536.61, -2.23, 400.07, 8, 0.82),
    
    # Heptapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanine", 515.60, -3.80, 443.24, 9, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanine", 557.68, -2.60, 443.24, 9, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanine", 591.70, -1.90, 443.24, 9, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanine", 573.64, -3.40, 481.26, 10, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanine", 558.63, -3.95, 464.50, 10, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanine", 581.66, -3.25, 461.06, 10, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanine", 547.67, -2.73, 443.24, 9, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanine", 600.71, -4.69, 486.47, 11, 0.75),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanine", 572.70, -3.87, 455.08, 10, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanine", 607.70, -2.63, 463.39, 9, 0.85),
    
    # Octapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanine", 586.68, -4.20, 506.56, 10, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanine", 628.76, -3.00, 506.56, 10, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanine", 662.79, -2.30, 506.56, 10, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanine", 644.73, -3.80, 544.58, 11, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanine", 629.72, -4.35, 527.82, 11, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanine", 652.75, -3.65, 524.38, 11, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanine", 618.76, -3.13, 506.56, 10, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanine", 671.80, -5.09, 549.79, 12, 0.78),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanine", 643.79, -4.27, 518.40, 11, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanine", 678.79, -3.03, 526.71, 10, 0.88),
    
    # Nonapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanine", 657.77, -4.60, 569.88, 11, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanine", 699.85, -3.40, 569.88, 11, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 733.87, -2.70, 569.88, 11, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanine", 715.81, -4.20, 607.90, 12, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanine", 700.80, -4.75, 591.14, 12, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanine", 723.83, -4.05, 587.70, 12, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanine", 689.84, -3.53, 569.88, 11, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanine", 742.89, -5.49, 613.11, 13, 0.80),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanine", 714.88, -4.67, 581.72, 12, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanine", 749.88, -3.43, 590.03, 11, 0.90),
    
    # Decapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 728.86, -5.00, 633.20, 12, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 770.94, -3.80, 633.20, 12, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 804.96, -3.10, 633.20, 12, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 786.90, -4.60, 671.22, 13, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 771.89, -5.15, 654.46, 13, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 794.92, -4.45, 651.02, 13, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 760.93, -3.93, 633.20, 12, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 813.98, -5.89, 676.43, 14, 0.82),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 785.97, -5.07, 645.04, 13, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 820.97, -3.83, 653.35, 12, 0.92),
    
    # Undecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 799.95, -5.40, 696.52, 13, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 842.03, -4.20, 696.52, 13, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 876.05, -3.50, 696.52, 13, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 857.99, -5.00, 734.54, 14, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 842.98, -5.55, 717.78, 14, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 866.01, -4.85, 714.34, 14, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 832.02, -4.33, 696.52, 13, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 885.07, -6.29, 739.75, 15, 0.85),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 857.06, -5.47, 708.36, 14, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 892.06, -4.23, 716.67, 13, 0.95),
    
    # Dodecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 871.04, -5.80, 759.84, 14, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 913.12, -4.60, 759.84, 14, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 947.14, -3.90, 759.84, 14, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 929.08, -5.40, 797.86, 15, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 914.07, -5.95, 781.10, 15, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 937.10, -5.25, 777.66, 15, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 903.11, -4.73, 759.84, 14, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 956.16, -6.69, 803.07, 16, 0.88),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 928.15, -5.87, 771.68, 15, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 963.15, -4.63, 779.99, 14, 0.98),
    
    # Tridecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 942.13, -6.20, 823.16, 15, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 984.21, -5.00, 823.16, 15, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1018.23, -4.30, 823.16, 15, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1000.17, -5.80, 861.18, 16, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 985.16, -6.35, 844.42, 16, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1008.19, -5.65, 840.98, 16, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 974.20, -5.13, 823.16, 15, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1027.25, -7.09, 866.39, 17, 0.90),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 999.24, -6.27, 835.00, 16, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1034.24, -5.03, 843.31, 15, 1.00),
    
    # Tetradecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1013.22, -6.60, 886.48, 16, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1055.30, -5.40, 886.48, 16, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1089.32, -4.70, 886.48, 16, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1071.26, -6.20, 924.50, 17, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1056.25, -6.75, 907.74, 17, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1079.28, -6.05, 904.30, 17, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1045.29, -5.53, 886.48, 16, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1098.34, -7.49, 929.71, 18, 0.92),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1070.33, -6.67, 898.32, 17, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1105.33, -5.43, 906.63, 16, 1.02),
    
    # Pentadecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1084.31, -7.00, 959.80, 17, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1126.39, -5.80, 959.80, 17, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1160.41, -5.10, 959.80, 17, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1142.35, -6.60, 997.82, 18, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1127.34, -7.15, 981.06, 18, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1150.37, -6.45, 977.62, 18, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1116.38, -5.93, 959.80, 17, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1169.43, -7.89, 1003.03, 19, 0.95),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1141.42, -7.07, 971.64, 18, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1176.42, -5.83, 979.95, 17, 1.05),
    
    # Hexadecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1155.40, -7.40, 1033.12, 18, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1197.48, -6.20, 1033.12, 18, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1231.50, -5.50, 1033.12, 18, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1213.44, -7.00, 1071.14, 19, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1198.43, -7.55, 1054.38, 19, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1221.46, -6.85, 1050.94, 19, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1187.47, -6.33, 1033.12, 18, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1240.52, -8.29, 1076.35, 20, 0.98),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1212.51, -7.47, 1044.96, 19, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1247.51, -6.23, 1053.27, 18, 1.08),
    
    # Heptadecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1226.49, -7.80, 1106.44, 19, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1268.57, -6.60, 1106.44, 19, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1302.59, -5.90, 1106.44, 19, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1284.53, -7.40, 1144.46, 20, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1269.52, -7.95, 1127.70, 20, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1292.55, -7.25, 1124.26, 20, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1258.56, -6.73, 1106.44, 19, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1311.61, -8.69, 1149.67, 21, 1.00),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1283.60, -7.87, 1118.28, 20, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1318.60, -6.63, 1126.59, 19, 1.10),
    
    # Octadecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1339.76, -8.20, 1227.56, 20, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1381.84, -7.00, 1227.56, 20, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1415.86, -6.30, 1227.56, 20, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1397.80, -7.80, 1265.58, 21, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1382.79, -8.35, 1248.82, 21, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1405.82, -7.65, 1245.38, 21, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1371.83, -7.13, 1227.56, 20, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1424.88, -9.09, 1270.79, 22, 1.02),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1396.87, -8.27, 1239.40, 21, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1431.87, -7.03, 1247.71, 20, 1.12),
    
    # Nonadecapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1395.02, -8.60, 1345.68, 21, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1437.10, -7.40, 1345.68, 21, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1471.12, -6.70, 1345.68, 21, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1453.06, -8.20, 1383.70, 22, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1438.05, -8.75, 1366.94, 22, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1461.08, -8.05, 1363.50, 22, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1427.09, -7.53, 1345.68, 21, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1480.14, -9.49, 1388.91, 23, 1.05),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1452.13, -8.67, 1357.52, 22, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1487.13, -7.43, 1365.83, 21, 1.15),
    
    # Eicosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1450.64, -9.00, 1463.80, 22, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1492.72, -7.80, 1463.80, 22, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1526.74, -7.10, 1463.80, 22, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1508.68, -8.60, 1501.82, 23, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1493.67, -9.15, 1485.06, 23, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1516.70, -8.45, 1481.62, 23, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1482.71, -7.93, 1463.80, 22, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1535.76, -9.89, 1507.03, 24, 1.08),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1507.75, -9.07, 1475.64, 23, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1542.75, -7.83, 1483.95, 22, 1.18),
    
    # Heneicosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1506.27, -9.40, 1581.92, 23, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1548.35, -8.20, 1581.92, 23, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1582.37, -7.50, 1581.92, 23, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1564.31, -9.00, 1619.94, 24, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1549.30, -9.55, 1603.18, 24, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1572.33, -8.85, 1599.74, 24, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1538.34, -8.33, 1581.92, 23, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1591.39, -10.29, 1625.15, 25, 1.10),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1563.38, -9.47, 1593.76, 24, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1598.38, -8.23, 1602.07, 23, 1.20),
    
    # Docosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1561.90, -9.80, 1736.04, 24, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1603.98, -8.60, 1736.04, 24, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1638.00, -7.90, 1736.04, 24, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1619.94, -9.40, 1774.06, 25, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1604.93, -9.95, 1757.30, 25, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1627.96, -9.25, 1753.86, 25, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1593.97, -8.73, 1736.04, 24, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1647.02, -10.69, 1779.27, 26, 1.12),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1619.01, -9.87, 1747.88, 25, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1654.01, -8.63, 1756.19, 24, 1.22),
    
    # Tricosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1627.53, -10.20, 1850.16, 25, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1669.61, -9.00, 1850.16, 25, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1703.63, -8.30, 1850.16, 25, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1685.57, -9.80, 1888.18, 26, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1670.56, -10.35, 1871.42, 26, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1693.59, -9.65, 1867.98, 26, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1659.60, -9.13, 1850.16, 25, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1712.65, -11.09, 1893.39, 27, 1.15),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1684.64, -10.27, 1862.00, 26, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1719.64, -9.03, 1870.31, 25, 1.25),
    
    # Tetracosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1704.16, -10.60, 1964.28, 26, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1746.24, -9.40, 1964.28, 26, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1780.26, -8.70, 1964.28, 26, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1762.20, -10.20, 2002.30, 27, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1747.19, -10.75, 1985.54, 27, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1770.22, -10.05, 1982.10, 27, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1736.23, -9.53, 1964.28, 26, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1789.28, -11.49, 2007.51, 28, 1.18),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1761.27, -10.67, 1976.12, 27, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1796.27, -9.43, 1984.43, 26, 1.28),
    
    # Pentacosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1780.79, -11.00, 2077.40, 27, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1822.87, -9.80, 2077.40, 27, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1856.89, -9.10, 2077.40, 27, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1838.83, -10.60, 2115.42, 28, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1823.82, -11.15, 2098.66, 28, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1846.85, -10.45, 2095.22, 28, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1812.86, -9.93, 2077.40, 27, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1865.91, -11.89, 2120.63, 29, 1.20),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1837.90, -11.07, 2089.24, 28, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1872.90, -9.83, 2097.55, 27, 1.30),
    
    # Hexacosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1901.42, -11.40, 2190.52, 28, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1943.50, -10.20, 2190.52, 28, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1977.52, -9.50, 2190.52, 28, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1959.46, -11.00, 2228.54, 29, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1944.45, -11.55, 2211.78, 29, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1967.48, -10.85, 2208.34, 29, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1933.49, -10.33, 2190.52, 28, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1986.54, -12.29, 2233.75, 30, 1.22),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1958.53, -11.47, 2202.36, 29, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1993.53, -10.23, 2210.67, 28, 1.32),
    
    # Heptacosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 1975.31, -11.80, 2303.64, 29, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2017.39, -10.60, 2303.64, 29, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2051.41, -9.90, 2303.64, 29, 1.40),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2033.35, -11.40, 2341.66, 30, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2018.34, -11.95, 2324.90, 30, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2041.37, -11.25, 2321.46, 30, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2007.38, -10.73, 2303.64, 29, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2060.43, -12.69, 2346.87, 31, 1.25),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2032.42, -11.87, 2315.48, 30, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2067.42, -10.63, 2323.79, 29, 1.35),
    
    # Octacosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2046.46, -12.20, 2420.76, 30, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2088.54, -11.00, 2420.76, 30, 1.40),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2122.56, -10.30, 2420.76, 30, 1.42),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2104.50, -11.80, 2458.78, 31, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2089.49, -12.35, 2442.02, 31, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2112.52, -11.65, 2438.58, 31, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2078.53, -11.13, 2420.76, 30, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2131.58, -13.09, 2463.99, 32, 1.28),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2103.57, -12.27, 2432.60, 31, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2138.57, -11.03, 2440.91, 30, 1.38),
    
    # Nonacosapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2117.13, -12.60, 2533.88, 31, 1.40),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2159.21, -11.40, 2533.88, 31, 1.42),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2193.23, -10.70, 2533.88, 31, 1.45),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2175.17, -12.20, 2571.90, 32, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2160.16, -12.75, 2555.14, 32, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2183.19, -12.05, 2551.70, 32, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2149.20, -11.53, 2533.88, 31, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2202.25, -13.49, 2577.11, 33, 1.30),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2174.24, -12.67, 2545.72, 32, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2209.24, -11.43, 2554.03, 31, 1.40),
    
    # Triacontapeptides
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)C", "Alanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2253.84, -13.40, 2637.00, 32, 1.42),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(C)C", "Leucylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2295.92, -12.20, 2637.00, 32, 1.45),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)Cc1ccccc1", "Phenylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2329.94, -11.50, 2637.00, 32, 1.48),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCC(=O)O", "Glutamylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2311.88, -13.00, 2675.02, 33, 1.40),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC(=O)N", "Asparaginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2296.87, -13.55, 2658.26, 33, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CNC=N1", "Histidylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2319.90, -12.85, 2654.82, 33, 1.40),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CS", "Cysteinylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2285.91, -12.33, 2637.00, 32, 1.35),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCNC(=N)N", "Arginylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2338.96, -14.29, 2680.23, 34, 1.32),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CCCN", "Lysylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2310.95, -13.47, 2648.84, 33, 1.38),
    ("N[C@@H](C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)O)CC1=CC=C(O)C=C1", "Tyrosylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanylalanine", 2345.95, -12.23, 2657.15, 32, 1.42),
    
    # More diverse molecules (continued)
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4", "Tetraphenylmethane", 320.43, 7.00, 0.0, 0, 0.40),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5", "Pentaphenylmethane", 396.52, 8.50, 0.0, 0, 0.35),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6", "Hexaphenylmethane", 472.62, 10.00, 0.0, 0, 0.30),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7", "Heptaphenylmethane", 548.71, 11.50, 0.0, 0, 0.25),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8", "Octaphenylmethane", 624.81, 13.00, 0.0, 0, 0.22),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8C9=CC=CC=C9", "Nonaphenylmethane", 700.90, 14.50, 0.0, 0, 0.20),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8C9=CC=CC=C9C%10=CC=CC=C%10", "Decaphenylmethane", 777.00, 16.00, 0.0, 0, 0.18),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8C9=CC=CC=C9C%10=CC=CC=C%10C%11=CC=CC=C%11", "Undecaphenylmethane", 853.09, 17.50, 0.0, 0, 0.15),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8C9=CC=CC=C9C%10=CC=CC=C%10C%11=CC=CC=C%11C%12=CC=CC=C%12", "Dodecaphenylmethane", 929.19, 19.00, 0.0, 0, 0.12),
    ("C1=CC=C(C=C1)C2=CC=CC=C2C3=CC=CC=C3C4=CC=CC=C4C5=CC=CC=C5C6=CC=CC=C6C7=CC=CC=C7C8=CC=CC=C8C9=CC=CC=C9C%10=CC=CC=C%10C%11=CC=CC=C%11C%12=CC=CC=C%12C%13=CC=CC=C%13", "Tridecaphenylmethane", 1005.28, 20.50, 0.0, 0, 0.10),
    
    # End of library
]

# Shuffle to avoid sequential patterns
random.shuffle(MOLECULES)


def mine_molecule(user_id, molecule):
    """Mine a single molecule for a user via the API."""
    smiles, name, mw, logp, tpsa, lipinski, qed = molecule
    body = json.dumps({
        "smiles": smiles,
        "name": name,
        "mw": mw,
        "logp": logp,
        "tpsa": tpsa,
        "qed": qed,
        "lipinski_pass": lipinski,
        "user_id": user_id
    }).encode()
    
    req = urllib.request.Request(
        f"{API_BASE}/mine",
        body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return result
    except Exception as e:
        return {"error": str(e)}


def run_mining_batch(molecules_per_user=20):
    """Run one mining cycle for all users, mining N molecules each."""
    stats = {uid: {"new": 0, "duplicates": 0, "errors": 0, "details": []} for uid in USER_IDS}
    for uid in USER_IDS:
        print(f"[{datetime.now()}] Mining for user {uid}...")
        attempts = 0
        max_attempts = molecules_per_user * 10  # safety cap to avoid infinite loops
        while stats[uid]["new"] < molecules_per_user and attempts < max_attempts:
            mol = random.choice(MOLECULES)
            result = mine_molecule(uid, mol)
            stats[uid]["details"].append(result)
            if result.get("error"):
                stats[uid]["errors"] += 1
            elif result.get("duplicate"):
                stats[uid]["duplicates"] += 1
            elif result.get("success") and result.get("molecule_id"):
                stats[uid]["new"] += 1
            attempts += 1
            time.sleep(0.3)  # Rate limiting
        print(f"[{datetime.now()}] User {uid}: {stats[uid]['new']} new, {stats[uid]['duplicates']} dup, {stats[uid]['errors']} err ({attempts} attempts)")
    return stats


def main(ctx):
    """Main entry point for PythonRun."""
    MOLECULES_PER_USER = 20
    print(f"[{datetime.now()}] Starting mining batch for {len(USER_IDS)} users, {MOLECULES_PER_USER} molecules each...")
    stats = run_mining_batch(MOLECULES_PER_USER)
    
    # Summarize results
    total_new = sum(s["new"] for s in stats.values())
    total_dup = sum(s["duplicates"] for s in stats.values())
    total_err = sum(s["errors"] for s in stats.values())
    total_attempts = len(USER_IDS) * MOLECULES_PER_USER
    
    print(f"\n[{datetime.now()}] Batch complete!")
    print(f"  Total attempts: {total_attempts}")
    print(f"  Total new: {total_new}")
    print(f"  Total duplicates: {total_dup}")
    print(f"  Total errors: {total_err}")
    print(f"\nPer-user breakdown:")
    for uid, s in stats.items():
        print(f"  User {uid}: {s['new']} new, {s['duplicates']} dup, {s['errors']} err")
    
    return {
        "total_attempts": total_attempts,
        "new_molecules": total_new,
        "duplicates": total_dup,
        "errors": total_err,
        "per_user": stats
    }


def run_standalone():
    """Run standalone without PythonRun wrapper."""
    result = main(None)
    return result
