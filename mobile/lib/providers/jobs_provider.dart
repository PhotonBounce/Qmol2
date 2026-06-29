import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/job.dart';
import '../services/api_service.dart';
import 'api_provider.dart';

class JobsNotifier extends StateNotifier<AsyncValue<List<Job>>> {
  final ApiService _api;

  JobsNotifier(this._api) : super(const AsyncValue.data([]));

  Future<void> createJob(List<String> smiles, String endpoint) async {
    state = const AsyncValue.loading();
    try {
      final job = await _api.createJob(smiles, endpoint);
      final current = state.value ?? [];
      state = AsyncValue.data([job, ...current]);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refreshJob(String jobId) async {
    try {
      final updated = await _api.getJob(jobId);
      final current = state.value ?? [];
      final idx = current.indexWhere((j) => j.id == jobId);
      if (idx >= 0) {
        final list = List<Job>.from(current);
        list[idx] = updated;
        state = AsyncValue.data(list);
      }
    } catch (e, st) {
      // Silently fail refresh; keep existing state
    }
  }

  Future<void> cancelJob(String jobId) async {
    try {
      await _api.cancelJob(jobId);
      await refreshJob(jobId);
    } catch (e, st) {
      // Silently fail
    }
  }

  void setJobs(List<Job> jobs) {
    state = AsyncValue.data(jobs);
  }

  void clear() => state = const AsyncValue.data([]);
}

final jobsProvider = StateNotifierProvider<JobsNotifier, AsyncValue<List<Job>>>((ref) {
  return JobsNotifier(ref.watch(apiServiceProvider));
});
