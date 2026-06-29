import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/compute_provider.dart';
import '../providers/auth_provider.dart';
import '../services/storage_service.dart';
import '../models/compute_result.dart';
import '../models/property.dart';
import '../models/molecule.dart';
import '../widgets/property_card.dart';
import '../widgets/smiles_input.dart';
import '../widgets/loading_indicator.dart';
import '../utils/constants.dart';

class ComputeScreen extends ConsumerStatefulWidget {
  const ComputeScreen({super.key});

  @override
  ConsumerState<ComputeScreen> createState() => _ComputeScreenState();
}

class _ComputeScreenState extends ConsumerState<ComputeScreen> {
  final _smilesController = TextEditingController();
  final _storage = StorageService();
  bool _hasResult = false;

  @override
  void dispose() {
    _smilesController.dispose();
    super.dispose();
  }

  Future<void> _compute() async {
    final smiles = _smilesController.text.trim();
    if (smiles.isEmpty) return;

    await ref.read(computeProvider.notifier).compute(smiles);
    setState(() => _hasResult = true);
  }

  Future<void> _saveResult() async {
    final result = ref.read(computeProvider).value;
    if (result == null) return;

    final history = await _storage.getHistory();
    final molecule = Molecule(
      smiles: result.smiles,
      name: result.name,
      computedAt: DateTime.now().toIso8601String(),
      results: [result],
    );
    history.insert(0, molecule);
    await _storage.saveHistory(history);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Saved to history')),
      );
    }
  }

  Future<void> _shareResult() async {
    final result = ref.read(computeProvider).value;
    if (result == null) return;

    final text = '''
Q-Mol Computation Results
SMILES: ${result.smiles}
MW: ${result.mw?.toStringAsFixed(2) ?? 'N/A'}
logP: ${result.logP?.toStringAsFixed(2) ?? 'N/A'}
TPSA: ${result.tpsa?.toStringAsFixed(2) ?? 'N/A'}
QED: ${result.qed?.toStringAsFixed(3) ?? 'N/A'}
Lipinski: ${result.lipinskiPass == true ? 'PASS' : 'FAIL'}
    '''.trim();

    await Share.share(text, subject: 'Q-Mol Results');
  }

  Future<void> _launch3D() async {
    final smiles = _smilesController.text.trim();
    if (smiles.isEmpty) return;

    final encoded = Uri.encodeComponent(smiles);
    final uri = Uri.parse('https://qmol.app/viewer?smiles=$encoded');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  List<Property> _buildProperties(ComputeResult r) {
    final props = <Property>[
      Property(name: 'Molecular Weight', value: r.mw, unit: 'Da', status: r.mw != null && r.mw! > 0 ? 'ok' : 'warning'),
      Property(name: 'logP', value: r.logP, status: 'ok'),
      Property(name: 'TPSA', value: r.tpsa, unit: 'Å²', status: 'ok'),
      Property(name: 'QED', value: r.qed, status: r.qed != null && r.qed! > 0.5 ? 'ok' : 'warning'),
      Property(name: 'HBD', value: r.hbd?.toDouble(), status: r.hbd != null && r.hbd! <= 5 ? 'ok' : 'warning'),
      Property(name: 'HBA', value: r.hba?.toDouble(), status: r.hba != null && r.hba! <= 10 ? 'ok' : 'warning'),
    ];

    if (r.lipinskiPass != null) {
      props.add(Property(
        name: 'Lipinski Rule of 5',
        value: r.lipinskiPass! ? 1.0 : 0.0,
        status: r.lipinskiPass! ? 'ok' : 'fail',
      ));
    }
    if (r.painsHit != null) {
      props.add(Property(
        name: 'PAINS Filter',
        value: r.painsHit! ? 0.0 : 1.0,
        status: r.painsHit! ? 'fail' : 'ok',
      ));
    }
    if (r.logS != null) {
      props.add(Property(name: 'logS (predicted)', value: r.logS, confidence: 0.82, status: 'ok'));
    }
    if (r.bbb != null) {
      props.add(Property(name: 'BBB Permeability', value: r.bbb, confidence: 0.78, status: 'ok'));
    }
    if (r.herg != null) {
      props.add(Property(name: 'hERG IC50', value: r.herg, unit: 'µM', confidence: 0.75, status: 'ok'));
    }
    if (r.gi != null) {
      props.add(Property(name: 'GI Absorption', value: r.gi, confidence: 0.80, status: 'ok'));
    }
    if (r.sa != null) {
      props.add(Property(name: 'Synthetic Accessibility', value: r.sa, confidence: 0.85, status: 'ok'));
    }

    return props;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final computeState = ref.watch(computeProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Compute'),
        actions: [
          if (_hasResult) ...[
            IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Save to history',
              onPressed: _saveResult,
            ),
            IconButton(
              icon: const Icon(Icons.share),
              tooltip: 'Share results',
              onPressed: _shareResult,
            ),
          ],
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: SmilesInput(
                controller: _smilesController,
                hintText: 'e.g., CCO (ethanol)',
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: computeState.isLoading ? null : _compute,
                      icon: computeState.isLoading
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.calculate, size: 20),
                      label: const Text('Compute'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: _launch3D,
                    icon: const Icon(Icons.threed_rotation, size: 20),
                    label: const Text('3D'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: computeState.when(
                data: (result) {
                  if (result == null) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.science, size: 64, color: theme.colorScheme.onSurface.withAlpha(100)),
                          const SizedBox(height: 16),
                          Text(
                            'Enter a SMILES to compute molecular properties',
                            style: theme.textTheme.bodyLarge,
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    );
                  }
                  final props = _buildProperties(result);
                  return ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: props.length,
                    itemBuilder: (context, index) => PropertyCard(property: props[index]),
                  );
                },
                loading: () => const LoadingIndicator(message: 'Computing...'),
                error: (err, _) => Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.error, size: 48, color: Constants.qmolError),
                        const SizedBox(height: 16),
                        Text('Error: $err', textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _compute,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
