import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

import '../models/api_key.dart';
import '../models/compute_result.dart';
import '../models/job.dart';
import '../models/molecule.dart';
import '../utils/constants.dart';
import 'storage_service.dart';

class HealthResponse {
  final bool healthy;
  final Map<String, dynamic>? checks;
  HealthResponse({required this.healthy, this.checks});
}

class ApiService {
  final Dio _dio;
  final StorageService _storage;
  final Connectivity _connectivity;

  bool _isOnline = true;
  final List<Map<String, dynamic>> _offlineQueue = [];

  ApiService({StorageService? storage, Dio? dio, Connectivity? connectivity})
      : _storage = storage ?? StorageService(),
        _dio = dio ?? Dio(),
        _connectivity = connectivity ?? Connectivity() {
    _dio.options.baseUrl = Constants.baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 15);
    _dio.options.receiveTimeout = const Duration(seconds: 30);
    _dio.options.headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final key = await _storage.getApiKey();
          if (key != null && key.isNotEmpty) {
            options.headers['x-api-key'] = key;
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.type == DioExceptionType.connectionTimeout ||
              error.type == DioExceptionType.connectionError ||
              error.response?.statusCode == 502 ||
              error.response?.statusCode == 503) {
            if (error.requestOptions.method != 'GET') {
              await _queueOfflineRequest(error.requestOptions);
            }
            return handler.resolve(
              Response(
                requestOptions: error.requestOptions,
                data: {'queued': true, 'offline': true},
                statusCode: 202,
              ),
            );
          }
          handler.next(error);
        },
      ),
    );

    // Retry interceptor
    _dio.interceptors.add(
      QueuedInterceptorsWrapper(
        onError: (error, handler) async {
          if (error.requestOptions.extra['retry_count'] == null) {
            error.requestOptions.extra['retry_count'] = 0;
          }
          final retryCount = error.requestOptions.extra['retry_count'] as int;
          if (retryCount < Constants.maxRetries &&
              (error.response == null ||
                  (error.response!.statusCode ?? 0) >= 500)) {
            error.requestOptions.extra['retry_count'] = retryCount + 1;
            final delay = Constants.retryBaseDelay * (1 << retryCount);
            await Future.delayed(delay);
            try {
              final response = await _dio.fetch(error.requestOptions);
              handler.resolve(response);
              return;
            } catch (e) {
              handler.next(error);
              return;
            }
          }
          handler.next(error);
        },
      ),
    );

    _connectivity.onConnectivityChanged.listen((result) {
      _isOnline = result != ConnectivityResult.none;
      if (_isOnline) _syncOfflineQueue();
    });
  }

  Future<void> _queueOfflineRequest(RequestOptions options) async {
    _offlineQueue.add({
      'method': options.method,
      'path': options.path,
      'data': options.data,
      'headers': Map<String, dynamic>.from(options.headers),
    });
  }

  Future<void> _syncOfflineQueue() async {
    while (_offlineQueue.isNotEmpty) {
      final req = _offlineQueue.removeAt(0);
      try {
        await _dio.request(
          req['path'] as String,
          data: req['data'],
          options: Options(
            method: req['method'] as String,
            headers: req['headers'] as Map<String, dynamic>,
          ),
        );
      } catch (e) {
        _offlineQueue.insert(0, req);
        break;
      }
    }
  }

  Future<ApiKey> signup(String email) async {
    final response = await _dio.post('/signup', data: {'email': email});
    final data = response.data as Map<String, dynamic>;
    return ApiKey(
      key: data['api_key'] as String,
      email: email,
      tier: data['tier'] as String? ?? 'free',
      monthlyQuota: data['monthly_quota'] as int? ?? Constants.freeQuota,
      usedQuota: data['used_quota'] as int? ?? 0,
      referral: data['referral'] as String?,
    );
  }

  Future<ComputeResult> compute(String smiles) async {
    final response = await _dio.post('/compute', data: {'smiles': [smiles]});
    final data = response.data as Map<String, dynamic>;
    final results = data['results'] as List<dynamic>;
    if (results.isEmpty) throw Exception('No results returned');
    return ComputeResult.fromJson(results.first as Map<String, dynamic>);
  }

  Future<ComputeResult> computeBatch(List<String> smiles) async {
    if (smiles.length == 1) return compute(smiles.first);
    final response = await _dio.post('/compute', data: {'smiles': smiles});
    final data = response.data as Map<String, dynamic>;
    final results = data['results'] as List<dynamic>;
    if (results.isEmpty) throw Exception('No results returned');
    // Return aggregate or first; for batch we use jobs endpoint
    return ComputeResult.fromJson(results.first as Map<String, dynamic>);
  }

  Future<Job> createJob(List<String> smiles, String endpoint) async {
    final response = await _dio.post('/jobs', data: {'smiles': smiles});
    final data = response.data as Map<String, dynamic>;
    return Job(
      id: data['job_id'] as String,
      status: data['status'] as String? ?? 'queued',
      total: data['n_smiles'] as int? ?? smiles.length,
      nSmiles: data['n_smiles'] as int? ?? smiles.length,
    );
  }

  Future<Job> getJob(String jobId) async {
    final response = await _dio.get('/jobs/$jobId');
    final data = response.data as Map<String, dynamic>;
    return Job(
      id: data['job_id'] as String,
      status: data['status'] as String,
      total: data['n_smiles'] as int? ?? 0,
      nSmiles: data['n_smiles'] as int? ?? 0,
      nProcessed: data['n_processed'] as int? ?? 0,
      error: data['error'] as String?,
      resultUrl: data['result_url'] as String?,
    );
  }

  Future<List<Job>> listJobs() async {
    // The API does not expose a list endpoint directly; jobs are tracked by id
    // Return empty list as placeholder; in production you'd store job IDs locally
    return [];
  }

  Future<HealthResponse> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return HealthResponse(
        healthy: response.statusCode == 200,
        checks: response.data as Map<String, dynamic>?,
      );
    } catch (e) {
      return HealthResponse(healthy: false);
    }
  }

  Future<void> cancelJob(String jobId) async {
    await _dio.delete('/jobs/$jobId');
  }

  Future<String> downloadJobResult(String jobId) async {
    final response = await _dio.get(
      '/jobs/$jobId/result',
      options: Options(responseType: ResponseType.plain),
    );
    return response.data as String;
  }
}
