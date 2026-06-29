import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import 'package:csv/csv.dart';

import '../providers/jobs_provider.dart';
import '../widgets/smiles_input.dart';
import '../widgets/loading_indicator.dart';
import '../utils/validators.dart';
import '../utils/constants.dart';

class BatchScreen extends ConsumerStatefulWidget {
  const BatchScreen({super.key});

  @override
  ConsumerState<BatchScreen> createState() => _BatchScreenState();
}

class _BatchScreenState extends ConsumerState<BatchScreen> {
  final _smilesController = TextEditingController();
  bool _isLoading = false;
  String? _jobId;
  String? _error;
  int _smilesCount = 0;

  void _onTextChanged(String text) {
    setState(() {
      _smilesCount = Validators.parseMultiSmiles(text).length;
    });
  }

  Future<void> _pickCsv() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv', 'txt'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    if (file.bytes == null) return;

    final content = String.fromCharCodes(file.bytes!);
    final rows = const CsvToListConverter().convert(content);
    if (rows.isEmpty) return;

    // Assume first column is SMILES
    final smiles = rows
        .where((row) => row.isNotEmpty)
        .map((row) => row.first.toString().trim())
        .where((s) => s.isNotEmpty && !s.toLowerCase().contains('smiles'))
        .toList();

    setState(() {
      _smilesController.text = smiles.join('\n');
      _smilesCount = smiles.length;
    });
  }

  Future<void> _runBatch() async {
    final smiles = Validators.parseMultiSmiles(_smilesController.text);
    if (smiles.isEmpty) {
      setState(() => _error = 'Enter at least one SMILES');
      return;
    }
    if (smiles.length > 200000) {
      setState(() => _error = 'Maximum 200,000 molecules per batch');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _jobId = null;
    });

    try {
      await ref.read(jobsProvider.notifier).createJob(smiles, '/jobs');
      final jobs = ref.read(jobsProvider).value;
      if (jobs != null && jobs.isNotEmpty) {
        setState(() => _jobId = jobs.first.id);
      }
    } catch (e) {
      setState(() => _error = 'Batch failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Batch Compute')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SmilesInput(
                controller: _smilesController,
                multiline: true,
                maxLines: 8,
                onChanged: _onTextChanged,
              ),
              const SizedBox(height: 8),
              Text(
                '$_smilesCount molecule${_smilesCount == 1 ? '' : 's'}',
                style: theme.textTheme.bodySmall,
                textAlign: TextAlign.right,
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _pickCsv,
                icon: const Icon(Icons.upload_file),
                label: const Text('Upload CSV'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _isLoading ? null : _runBatch,
                icon: _isLoading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.batch_prediction),
                label: Text(_isLoading ? 'Submitting...' : 'Run Batch'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Constants.qmolAccent,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  style: TextStyle(color: Constants.qmolError),
                  textAlign: TextAlign.center,
                ),
              ],
              if (_jobId != null) ...[
                const SizedBox(height: 24),
                Card(
                  color: Constants.qmolAccent.withAlpha(30),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: Constants.qmolAccent.withAlpha(100)),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Job Submitted!', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        SelectableText(
                          'Job ID: $_jobId',
                          style: theme.textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 8),
                        ElevatedButton(
                          onPressed: () => context.go(Constants.routeJobs),
                          child: const Text('View Progress'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Text(
                'Tip: Enter SMILES one per line, or upload a CSV where the first column contains SMILES strings.',
                style: theme.textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _smilesController.dispose();
    super.dispose();
  }
}
