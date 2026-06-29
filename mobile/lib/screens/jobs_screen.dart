import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';

import '../providers/jobs_provider.dart';
import '../services/api_service.dart';
import '../services/notification_service.dart';
import '../models/job.dart';
import '../widgets/job_list_item.dart';
import '../widgets/loading_indicator.dart';
import '../utils/constants.dart';

class JobsScreen extends ConsumerStatefulWidget {
  const JobsScreen({super.key});

  @override
  ConsumerState<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends ConsumerState<JobsScreen> {
  Timer? _pollTimer;
  final _notificationService = NotificationService();

  @override
  void initState() {
    super.initState();
    _notificationService.init();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) => _refreshJobs());
  }

  Future<void> _refreshJobs() async {
    final jobs = ref.read(jobsProvider).value ?? [];
    for (final job in jobs) {
      if (job.status == 'running' || job.status == 'queued' || job.status == 'processing') {
        await ref.read(jobsProvider.notifier).refreshJob(job.id);
        final updated = ref.read(jobsProvider).value?.firstWhere((j) => j.id == job.id, orElse: () => job);
        if (updated != null && (updated.status == 'done' || updated.status == 'completed')) {
          await _notificationService.showJobComplete(updated.id, updated.nProcessed);
        } else if (updated != null && updated.status == 'failed') {
          await _notificationService.showJobFailed(updated.id, updated.error ?? 'Unknown error');
        }
      }
    }
  }

  Future<void> _cancelJob(Job job) async {
    await ref.read(jobsProvider.notifier).cancelJob(job.id);
  }

  Future<void> _downloadResult(Job job) async {
    try {
      final api = ApiService();
      final result = await api.downloadJobResult(job.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Result downloaded: ${result.length} bytes')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Download failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final jobsState = ref.watch(jobsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Jobs'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _refreshJobs,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refreshJobs,
        child: jobsState.when(
          data: (jobs) {
            if (jobs.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.work_outline, size: 64, color: Colors.grey.withAlpha(150)),
                    const SizedBox(height: 16),
                    const Text('No jobs yet. Submit a batch to get started.'),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () => context.go(Constants.routeBatch),
                      child: const Text('Create Batch'),
                    ),
                  ],
                ),
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: jobs.length,
              itemBuilder: (context, index) {
                final job = jobs[index];
                return JobListItem(
                  job: job,
                  onTap: () {
                    // Navigate to detail or expand
                  },
                  onCancel: () => _cancelJob(job),
                  onDownload: () => _downloadResult(job),
                );
              },
            );
          },
          loading: () => const LoadingIndicator(message: 'Loading jobs...'),
          error: (err, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error, size: 48, color: Constants.qmolError),
                const SizedBox(height: 16),
                Text('Error: $err'),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _refreshJobs,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}
