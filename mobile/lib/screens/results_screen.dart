import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';
import 'package:csv/csv.dart';

import '../models/compute_result.dart';
import '../widgets/property_card.dart';
import '../widgets/loading_indicator.dart';
import '../utils/constants.dart';

class ResultsScreen extends ConsumerStatefulWidget {
  const ResultsScreen({super.key});

  @override
  ConsumerState<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends ConsumerState<ResultsScreen> {
  List<ComputeResult> _results = [];
  bool _loading = true;
  String? _error;
  String _sortColumn = 'smiles';
  bool _sortAscending = true;

  @override
  void initState() {
    super.initState();
    _loadResults();
  }

  Future<void> _loadResults() async {
    // In production, load from job result download or local storage
    // For now, show empty state
    setState(() {
      _loading = false;
      _results = [];
    });
  }

  void _sort(String column) {
    setState(() {
      if (_sortColumn == column) {
        _sortAscending = !_sortAscending;
      } else {
        _sortColumn = column;
        _sortAscending = true;
      }
      _results.sort((a, b) {
        int cmp;
        switch (column) {
          case 'smiles':
            cmp = a.smiles.compareTo(b.smiles);
            break;
          case 'mw':
            cmp = (a.mw ?? 0).compareTo(b.mw ?? 0);
            break;
          case 'logP':
            cmp = (a.logP ?? 0).compareTo(b.logP ?? 0);
            break;
          case 'qed':
            cmp = (a.qed ?? 0).compareTo(b.qed ?? 0);
            break;
          default:
            cmp = 0;
        }
        return _sortAscending ? cmp : -cmp;
      });
    });
  }

  Future<void> _exportCsv() async {
    if (_results.isEmpty) return;

    final rows = <List<String>>[
      ['SMILES', 'Name', 'MW', 'logP', 'TPSA', 'QED', 'HBD', 'HBA', 'Lipinski', 'PAINS', 'logS', 'BBB', 'hERG', 'GI', 'SA'],
    ];
    for (final r in _results) {
      rows.add([
        r.smiles,
        r.name ?? '',
        r.mw?.toString() ?? '',
        r.logP?.toString() ?? '',
        r.tpsa?.toString() ?? '',
        r.qed?.toString() ?? '',
        r.hbd?.toString() ?? '',
        r.hba?.toString() ?? '',
        r.lipinskiPass == true ? 'PASS' : 'FAIL',
        r.painsHit == true ? 'HIT' : 'CLEAR',
        r.logS?.toString() ?? '',
        r.bbb?.toString() ?? '',
        r.herg?.toString() ?? '',
        r.gi?.toString() ?? '',
        r.sa?.toString() ?? '',
      ]);
    }

    final csv = const ListToCsvConverter().convert(rows);
    await Share.share(csv, subject: 'Q-Mol Batch Results');
  }

  Future<void> _shareResults() async {
    if (_results.isEmpty) return;
    final buffer = StringBuffer('Q-Mol Batch Results\n\n');
    for (final r in _results) {
      buffer.writeln('SMILES: ${r.smiles}');
      buffer.writeln('MW: ${r.mw?.toStringAsFixed(2) ?? 'N/A'} | logP: ${r.logP?.toStringAsFixed(2) ?? 'N/A'} | QED: ${r.qed?.toStringAsFixed(3) ?? 'N/A'}');
      buffer.writeln();
    }
    await Share.share(buffer.toString(), subject: 'Q-Mol Batch Results');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) return const Scaffold(body: LoadingIndicator(message: 'Loading results...'));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Results'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            tooltip: 'Export CSV',
            onPressed: _results.isEmpty ? null : _exportCsv,
          ),
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share',
            onPressed: _results.isEmpty ? null : _shareResults,
          ),
        ],
      ),
      body: _results.isEmpty
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.table_chart, size: 64, color: Colors.grey.withAlpha(150)),
                  const SizedBox(height: 16),
                  const Text('No results to display.'),
                ],
              ),
            )
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                sortColumnIndex: ['smiles', 'mw', 'logP', 'qed'].indexOf(_sortColumn),
                sortAscending: _sortAscending,
                columns: [
                  DataColumn(label: const Text('SMILES'), onSort: (_) => _sort('smiles')),
                  DataColumn(label: const Text('MW'), numeric: true, onSort: (_) => _sort('mw')),
                  DataColumn(label: const Text('logP'), numeric: true, onSort: (_) => _sort('logP')),
                  DataColumn(label: const Text('QED'), numeric: true, onSort: (_) => _sort('qed')),
                  const DataColumn(label: Text('Lipinski')),
                  const DataColumn(label: Text('PAINS')),
                ],
                rows: _results.map((r) {
                  return DataRow(
                    cells: [
                      DataCell(Text(r.smiles, maxLines: 1, overflow: TextOverflow.ellipsis)),
                      DataCell(Text(r.mw?.toStringAsFixed(2) ?? 'N/A')),
                      DataCell(Text(r.logP?.toStringAsFixed(2) ?? 'N/A')),
                      DataCell(Text(r.qed?.toStringAsFixed(3) ?? 'N/A')),
                      DataCell(
                        Icon(
                          r.lipinskiPass == true ? Icons.check_circle : Icons.cancel,
                          color: r.lipinskiPass == true ? Constants.qmolSuccess : Constants.qmolError,
                          size: 18,
                        ),
                      ),
                      DataCell(
                        Icon(
                          r.painsHit == true ? Icons.warning : Icons.check_circle,
                          color: r.painsHit == true ? Constants.qmolError : Constants.qmolSuccess,
                          size: 18,
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
    );
  }
}
