import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';
import 'compute_result.dart';

part 'molecule.freezed.dart';
part 'molecule.g.dart';

@freezed
class Molecule with _$Molecule {
  const factory Molecule({
    required String smiles,
    String? name,
    String? computedAt,
    @Default([]) List<ComputeResult> results,
  }) = _Molecule;

  factory Molecule.fromJson(Map<String, Object?> json) => _$MoleculeFromJson(json);
}
