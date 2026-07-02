// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'compute_result.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ComputeResultImpl _$$ComputeResultImplFromJson(Map<String, dynamic> json) =>
    _$ComputeResultImpl(
      smiles: json['smiles'] as String,
      name: json['name'] as String?,
      formula: json['formula'] as String?,
      mw: (json['mw'] as num?)?.toDouble(),
      exactMass: (json['exactMass'] as num?)?.toDouble(),
      logP: (json['logP'] as num?)?.toDouble(),
      tpsa: (json['tpsa'] as num?)?.toDouble(),
      qed: (json['qed'] as num?)?.toDouble(),
      hbd: (json['hbd'] as num?)?.toInt(),
      hba: (json['hba'] as num?)?.toInt(),
      rotatableBonds: (json['rotatableBonds'] as num?)?.toInt(),
      aromaticRings: (json['aromaticRings'] as num?)?.toInt(),
      lipinskiPass: json['lipinskiPass'] as bool?,
      veberPass: json['veberPass'] as bool?,
      ghosePass: json['ghosePass'] as bool?,
      eganPass: json['eganPass'] as bool?,
      painsHit: json['painsHit'] as bool?,
      logS: (json['logS'] as num?)?.toDouble(),
      bbb: (json['bbb'] as num?)?.toDouble(),
      herg: (json['herg'] as num?)?.toDouble(),
      gi: (json['gi'] as num?)?.toDouble(),
      sa: (json['sa'] as num?)?.toDouble(),
      alerts: (json['alerts'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      descriptors: (json['descriptors'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      properties: (json['properties'] as List<dynamic>?)
              ?.map((e) => Property.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      computedAt: json['computedAt'] as String?,
      error: json['error'] as String?,
      status: json['status'] as String?,
    );

Map<String, dynamic> _$$ComputeResultImplToJson(_$ComputeResultImpl instance) =>
    <String, dynamic>{
      'smiles': instance.smiles,
      'name': instance.name,
      'formula': instance.formula,
      'mw': instance.mw,
      'exactMass': instance.exactMass,
      'logP': instance.logP,
      'tpsa': instance.tpsa,
      'qed': instance.qed,
      'hbd': instance.hbd,
      'hba': instance.hba,
      'rotatableBonds': instance.rotatableBonds,
      'aromaticRings': instance.aromaticRings,
      'lipinskiPass': instance.lipinskiPass,
      'veberPass': instance.veberPass,
      'ghosePass': instance.ghosePass,
      'eganPass': instance.eganPass,
      'painsHit': instance.painsHit,
      'logS': instance.logS,
      'bbb': instance.bbb,
      'herg': instance.herg,
      'gi': instance.gi,
      'sa': instance.sa,
      'alerts': instance.alerts,
      'descriptors': instance.descriptors,
      'properties': instance.properties,
      'computedAt': instance.computedAt,
      'error': instance.error,
      'status': instance.status,
    };
