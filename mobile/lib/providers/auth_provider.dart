import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/api_key.dart';
import '../services/storage_service.dart';
import '../services/api_service.dart';

enum AuthState { unknown, authenticated, unauthenticated }

class AuthNotifier extends StateNotifier<AsyncValue<AuthState>> {
  final StorageService _storage;
  final ApiService _api;

  AuthNotifier({
    StorageService? storage,
    ApiService? api,
  })  : _storage = storage ?? StorageService(),
        _api = api ?? ApiService(),
        super(const AsyncValue.loading()) {
    checkAuth();
  }

  Future<void> checkAuth() async {
    state = const AsyncValue.loading();
    try {
      final key = await _storage.getApiKey();
      if (key != null && key.isNotEmpty) {
        final health = await _api.checkHealth();
        if (health.healthy) {
          state = const AsyncValue.data(AuthState.authenticated);
        } else {
          state = const AsyncValue.data(AuthState.unauthenticated);
        }
      } else {
        state = const AsyncValue.data(AuthState.unauthenticated);
      }
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> login(ApiKey apiKey) async {
    await _storage.saveApiKey(apiKey.key);
    state = const AsyncValue.data(AuthState.authenticated);
  }

  Future<void> logout() async {
    await _storage.deleteApiKey();
    state = const AsyncValue.data(AuthState.unauthenticated);
  }

  Future<String?> getApiKey() => _storage.getApiKey();
}

final authProvider =
    StateNotifierProvider<AuthNotifier, AsyncValue<AuthState>>((ref) {
  return AuthNotifier();
});
