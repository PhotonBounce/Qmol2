import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'job.freezed.dart';
part 'job.g.dart';

@freezed
class Job with _$Job {
  const factory Job({
    required String id,
    required String status,
    @Default(0) int progress,
    @Default(0) int total,
    @Default(0) int nSmiles,
    @Default(0) int nProcessed,
    String? createdAt,
    String? finishedAt,
    String? error,
    String? resultUrl,
    String? endpoint,
  }) = _Job;

  factory Job.fromJson(Map<String, Object?> json) => _$JobFromJson(json);
}
