import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'api_key.freezed.dart';
part 'api_key.g.dart';

@freezed
class ApiKey with _$ApiKey {
  const factory ApiKey({
    required String key,
    required String email,
    required String tier,
    required int monthlyQuota,
    @Default(0) int usedQuota,
    String? referral,
  }) = _ApiKey;

  factory ApiKey.fromJson(Map<String, Object?> json) => _$ApiKeyFromJson(json);
}
