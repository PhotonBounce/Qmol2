import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/compute_result.dart';
import '../services/api_service.dart';
import 'api_provider.dart';

class ComputeNotifier extends StateNotifier<AsyncValue<ComputeResult?>> {
  final ApiService _api;

  ComputeNotifier(this._api) : super(const AsyncValue.data(null));

  Future<void> compute(String smiles) async {
    state = const AsyncValue.loading();
    try {
      final result = await _api.compute(smiles);
      state = AsyncValue.data(result);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> computeBatch(List<String> smiles) async {
    state = const AsyncValue.loading();
    try {
      final result = await _api.computeBatch(smiles);
      state = AsyncValue.data(result);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void clear() => state = const AsyncValue.data(null);
}

final computeProvider =
    StateNotifierProvider<ComputeNotifier, AsyncValue<ComputeResult?>>((ref) {
  return ComputeNotifier(ref.watch(apiServiceProvider));
});
