// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'property.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$PropertyImpl _$$PropertyImplFromJson(Map<String, dynamic> json) =>
    _$PropertyImpl(
      name: json['name'] as String,
      value: (json['value'] as num?)?.toDouble(),
      unit: json['unit'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      inDomain: json['inDomain'] as bool? ?? true,
      status: json['status'] as String? ?? 'ok',
    );

Map<String, dynamic> _$$PropertyImplToJson(_$PropertyImpl instance) =>
    <String, dynamic>{
      'name': instance.name,
      'value': instance.value,
      'unit': instance.unit,
      'confidence': instance.confidence,
      'inDomain': instance.inDomain,
      'status': instance.status,
    };
