// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'molecule.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Molecule _$MoleculeFromJson(Map<String, dynamic> json) {
  return _Molecule.fromJson(json);
}

/// @nodoc
mixin _$Molecule {
  String get smiles => throw _privateConstructorUsedError;
  String? get name => throw _privateConstructorUsedError;
  String? get computedAt => throw _privateConstructorUsedError;
  List<ComputeResult> get results => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $MoleculeCopyWith<Molecule> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $MoleculeCopyWith<$Res> {
  factory $MoleculeCopyWith(Molecule value, $Res Function(Molecule) then) =
      _$MoleculeCopyWithImpl<$Res, Molecule>;
  @useResult
  $Res call(
      {String smiles,
      String? name,
      String? computedAt,
      List<ComputeResult> results});
}

/// @nodoc
class _$MoleculeCopyWithImpl<$Res, $Val extends Molecule>
    implements $MoleculeCopyWith<$Res> {
  _$MoleculeCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? smiles = null,
    Object? name = freezed,
    Object? computedAt = freezed,
    Object? results = null,
  }) {
    return _then(_value.copyWith(
      smiles: null == smiles
          ? _value.smiles
          : smiles // ignore: cast_nullable_to_non_nullable
              as String,
      name: freezed == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String?,
      computedAt: freezed == computedAt
          ? _value.computedAt
          : computedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      results: null == results
          ? _value.results
          : results // ignore: cast_nullable_to_non_nullable
              as List<ComputeResult>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$MoleculeImplCopyWith<$Res>
    implements $MoleculeCopyWith<$Res> {
  factory _$$MoleculeImplCopyWith(
          _$MoleculeImpl value, $Res Function(_$MoleculeImpl) then) =
      __$$MoleculeImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String smiles,
      String? name,
      String? computedAt,
      List<ComputeResult> results});
}

/// @nodoc
class __$$MoleculeImplCopyWithImpl<$Res>
    extends _$MoleculeCopyWithImpl<$Res, _$MoleculeImpl>
    implements _$$MoleculeImplCopyWith<$Res> {
  __$$MoleculeImplCopyWithImpl(
      _$MoleculeImpl _value, $Res Function(_$MoleculeImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? smiles = null,
    Object? name = freezed,
    Object? computedAt = freezed,
    Object? results = null,
  }) {
    return _then(_$MoleculeImpl(
      smiles: null == smiles
          ? _value.smiles
          : smiles // ignore: cast_nullable_to_non_nullable
              as String,
      name: freezed == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String?,
      computedAt: freezed == computedAt
          ? _value.computedAt
          : computedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      results: null == results
          ? _value._results
          : results // ignore: cast_nullable_to_non_nullable
              as List<ComputeResult>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$MoleculeImpl with DiagnosticableTreeMixin implements _Molecule {
  const _$MoleculeImpl(
      {required this.smiles,
      this.name,
      this.computedAt,
      final List<ComputeResult> results = const []})
      : _results = results;

  factory _$MoleculeImpl.fromJson(Map<String, dynamic> json) =>
      _$$MoleculeImplFromJson(json);

  @override
  final String smiles;
  @override
  final String? name;
  @override
  final String? computedAt;
  final List<ComputeResult> _results;
  @override
  @JsonKey()
  List<ComputeResult> get results {
    if (_results is EqualUnmodifiableListView) return _results;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_results);
  }

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'Molecule(smiles: $smiles, name: $name, computedAt: $computedAt, results: $results)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'Molecule'))
      ..add(DiagnosticsProperty('smiles', smiles))
      ..add(DiagnosticsProperty('name', name))
      ..add(DiagnosticsProperty('computedAt', computedAt))
      ..add(DiagnosticsProperty('results', results));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$MoleculeImpl &&
            (identical(other.smiles, smiles) || other.smiles == smiles) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.computedAt, computedAt) ||
                other.computedAt == computedAt) &&
            const DeepCollectionEquality().equals(other._results, _results));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, smiles, name, computedAt,
      const DeepCollectionEquality().hash(_results));

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$MoleculeImplCopyWith<_$MoleculeImpl> get copyWith =>
      __$$MoleculeImplCopyWithImpl<_$MoleculeImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$MoleculeImplToJson(
      this,
    );
  }
}

abstract class _Molecule implements Molecule {
  const factory _Molecule(
      {required final String smiles,
      final String? name,
      final String? computedAt,
      final List<ComputeResult> results}) = _$MoleculeImpl;

  factory _Molecule.fromJson(Map<String, dynamic> json) =
      _$MoleculeImpl.fromJson;

  @override
  String get smiles;
  @override
  String? get name;
  @override
  String? get computedAt;
  @override
  List<ComputeResult> get results;
  @override
  @JsonKey(ignore: true)
  _$$MoleculeImplCopyWith<_$MoleculeImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
