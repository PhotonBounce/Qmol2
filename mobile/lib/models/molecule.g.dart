// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'molecule.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$MoleculeImpl _$$MoleculeImplFromJson(Map<String, dynamic> json) =>
    _$MoleculeImpl(
      smiles: json['smiles'] as String,
      name: json['name'] as String?,
      computedAt: json['computedAt'] as String?,
      results: (json['results'] as List<dynamic>?)
              ?.map((e) => ComputeResult.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$MoleculeImplToJson(_$MoleculeImpl instance) =>
    <String, dynamic>{
      'smiles': instance.smiles,
      'name': instance.name,
      'computedAt': instance.computedAt,
      'results': instance.results,
    };
