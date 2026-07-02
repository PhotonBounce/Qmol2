// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'api_key.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ApiKeyImpl _$$ApiKeyImplFromJson(Map<String, dynamic> json) => _$ApiKeyImpl(
      key: json['key'] as String,
      email: json['email'] as String,
      tier: json['tier'] as String,
      monthlyQuota: (json['monthlyQuota'] as num).toInt(),
      usedQuota: (json['usedQuota'] as num?)?.toInt() ?? 0,
      referral: json['referral'] as String?,
    );

Map<String, dynamic> _$$ApiKeyImplToJson(_$ApiKeyImpl instance) =>
    <String, dynamic>{
      'key': instance.key,
      'email': instance.email,
      'tier': instance.tier,
      'monthlyQuota': instance.monthlyQuota,
      'usedQuota': instance.usedQuota,
      'referral': instance.referral,
    };
