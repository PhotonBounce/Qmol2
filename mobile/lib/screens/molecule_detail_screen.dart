import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/compute_result.dart';
import '../models/property.dart';
import '../widgets/property_card.dart';
import '../widgets/loading_indicator.dart';
import '../utils/constants.dart';

class MoleculeDetailScreen extends StatefulWidget {
  final String smiles;

  const MoleculeDetailScreen({super.key, required this.smiles});

  @override
  State<MoleculeDetailScreen> createState() => _MoleculeDetailScreenState();
}

class _MoleculeDetailScreenState extends State<MoleculeDetailScreen> {
  ComputeResult? _result;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadMolecule();
  }

  Future<void> _loadMolecule() async {
    // In production, fetch from local storage or API
    // For now, create a placeholder
    setState(() {
      _result = ComputeResult(
        smiles: widget.smiles,
        name: 'Molecule',
        mw: 180.16,
        logP: 2.5,
        tpsa: 46.53,
        qed: 0.72,
        hbd: 1,
        hba: 3,
        lipinskiPass: true,
        painsHit: false,
      );
      _loading = false;
    });
  }

  Future<void> _similaritySearch() async {
    final encoded = Uri.encodeComponent(widget.smiles);
    final uri = Uri.parse('https://qmol.app/similarity?smiles=$encoded');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _addToCollection() async {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Added to collection')),
      );
    }
  }

  List<Property> _buildProperties(ComputeResult r) {
    return [
      Property(name: 'SMILES', value: null, status: 'ok'),
      Property(name: 'Molecular Weight', value: r.mw, unit: 'Da'),
      Property(name: 'logP', value: r.logP),
      Property(name: 'TPSA', value: r.tpsa, unit: 'Å²'),
      Property(name: 'QED', value: r.qed),
      Property(name: 'HBD', value: r.hbd?.toDouble()),
      Property(name: 'HBA', value: r.hba?.toDouble()),
      Property(name: 'Lipinski', value: r.lipinskiPass == true ? 1.0 : 0.0, status: r.lipinskiPass == true ? 'ok' : 'fail'),
      Property(name: 'PAINS', value: r.painsHit == true ? 0.0 : 1.0, status: r.painsHit == true ? 'fail' : 'ok'),
      if (r.logS != null) Property(name: 'logS (predicted)', value: r.logS, confidence: 0.82),
      if (r.bbb != null) Property(name: 'BBB Permeability', value: r.bbb, confidence: 0.78),
      if (r.herg != null) Property(name: 'hERG IC50', value: r.herg, unit: 'µM', confidence: 0.75),
      if (r.gi != null) Property(name: 'GI Absorption', value: r.gi, confidence: 0.80),
      if (r.sa != null) Property(name: 'Synthetic Accessibility', value: r.sa, confidence: 0.85),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Molecule'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Similarity search',
            onPressed: _similaritySearch,
          ),
          IconButton(
            icon: const Icon(Icons.bookmark_add),
            tooltip: 'Add to collection',
            onPressed: _addToCollection,
          ),
        ],
      ),
      body: _loading
          ? const LoadingIndicator(message: 'Loading molecule...')
          : _result == null
              ? const Center(child: Text('Molecule not found'))
              : CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Card(
                              elevation: 2,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  children: [
                                    Icon(Icons.science, size: 64, color: Constants.qmolAccent),
                                    const SizedBox(height: 8),
                                    SelectableText(
                                      widget.smiles,
                                      style: theme.textTheme.titleMedium,
                                      textAlign: TextAlign.center,
                                    ),
                                    if (_result!.name != null) ...[
                                      const SizedBox(height: 4),
                                      Text(_result!.name!, style: theme.textTheme.bodyMedium),
                                    ],
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text('Properties', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 8),
                          ],
                        ),
                      ),
                    ),
                    SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final props = _buildProperties(_result!);
                          return PropertyCard(property: props[index]);
                        },
                        childCount: _buildProperties(_result!).length,
                      ),
                    ),
                  ],
                ),
    );
  }
}
