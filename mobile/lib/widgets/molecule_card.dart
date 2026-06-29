import 'package:flutter/material.dart';
import '../models/molecule.dart';
import '../utils/constants.dart';

class MoleculeCard extends StatelessWidget {
  final Molecule molecule;
  final VoidCallback? onTap;

  const MoleculeCard({super.key, required this.molecule, this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Semantics(
      label: 'Molecule ${molecule.name ?? molecule.smiles}, tap for details',
      child: Card(
        elevation: 2,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.science,
                      color: Constants.qmolAccent,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        molecule.smiles,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                if (molecule.name != null && molecule.name!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    molecule.name!,
                    style: theme.textTheme.bodySmall,
                  ),
                ],
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.access_time,
                      size: 14,
                      color: theme.colorScheme.onSurface.withAlpha(150),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      molecule.computedAt ?? 'Recently',
                      style: theme.textTheme.bodySmall,
                    ),
                    const Spacer(),
                    Text(
                      '${molecule.results.length} result${molecule.results.length == 1 ? '' : 's'}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
