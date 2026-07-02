// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'job.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$JobImpl _$$JobImplFromJson(Map<String, dynamic> json) => _$JobImpl(
      id: json['id'] as String,
      status: json['status'] as String,
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      total: (json['total'] as num?)?.toInt() ?? 0,
      nSmiles: (json['nSmiles'] as num?)?.toInt() ?? 0,
      nProcessed: (json['nProcessed'] as num?)?.toInt() ?? 0,
      createdAt: json['createdAt'] as String?,
      finishedAt: json['finishedAt'] as String?,
      error: json['error'] as String?,
      resultUrl: json['resultUrl'] as String?,
      endpoint: json['endpoint'] as String?,
    );

Map<String, dynamic> _$$JobImplToJson(_$JobImpl instance) => <String, dynamic>{
      'id': instance.id,
      'status': instance.status,
      'progress': instance.progress,
      'total': instance.total,
      'nSmiles': instance.nSmiles,
      'nProcessed': instance.nProcessed,
      'createdAt': instance.createdAt,
      'finishedAt': instance.finishedAt,
      'error': instance.error,
      'resultUrl': instance.resultUrl,
      'endpoint': instance.endpoint,
    };
