import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';
import 'property.dart';

part 'compute_result.freezed.dart';
part 'compute_result.g.dart';

@freezed
class ComputeResult with _$ComputeResult {
  const factory ComputeResult({
    required String smiles,
    String? name,
    String? formula,
    double? mw,
    double? exactMass,
    double? logP,
    double? tpsa,
    double? qed,
    int? hbd,
    int? hba,
    int? rotatableBonds,
    int? aromaticRings,
    bool? lipinskiPass,
    bool? veberPass,
    bool? ghosePass,
    bool? eganPass,
    bool? painsHit,
    double? logS,
    double? bbb,
    double? herg,
    double? gi,
    double? sa,
    @Default([]) List<String> alerts,
    @Default([]) List<String> descriptors,
    @Default([]) List<Property> properties,
    String? computedAt,
    String? error,
    String? status,
  }) = _ComputeResult;

  factory ComputeResult.fromJson(Map<String, Object?> json) =>
      _$ComputeResultFromJson(json);
}
