// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'api_key.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ApiKey _$ApiKeyFromJson(Map<String, dynamic> json) {
  return _ApiKey.fromJson(json);
}

/// @nodoc
mixin _$ApiKey {
  String get key => throw _privateConstructorUsedError;
  String get email => throw _privateConstructorUsedError;
  String get tier => throw _privateConstructorUsedError;
  int get monthlyQuota => throw _privateConstructorUsedError;
  int get usedQuota => throw _privateConstructorUsedError;
  String? get referral => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $ApiKeyCopyWith<ApiKey> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ApiKeyCopyWith<$Res> {
  factory $ApiKeyCopyWith(ApiKey value, $Res Function(ApiKey) then) =
      _$ApiKeyCopyWithImpl<$Res, ApiKey>;
  @useResult
  $Res call(
      {String key,
      String email,
      String tier,
      int monthlyQuota,
      int usedQuota,
      String? referral});
}

/// @nodoc
class _$ApiKeyCopyWithImpl<$Res, $Val extends ApiKey>
    implements $ApiKeyCopyWith<$Res> {
  _$ApiKeyCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? key = null,
    Object? email = null,
    Object? tier = null,
    Object? monthlyQuota = null,
    Object? usedQuota = null,
    Object? referral = freezed,
  }) {
    return _then(_value.copyWith(
      key: null == key
          ? _value.key
          : key // ignore: cast_nullable_to_non_nullable
              as String,
      email: null == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String,
      tier: null == tier
          ? _value.tier
          : tier // ignore: cast_nullable_to_non_nullable
              as String,
      monthlyQuota: null == monthlyQuota
          ? _value.monthlyQuota
          : monthlyQuota // ignore: cast_nullable_to_non_nullable
              as int,
      usedQuota: null == usedQuota
          ? _value.usedQuota
          : usedQuota // ignore: cast_nullable_to_non_nullable
              as int,
      referral: freezed == referral
          ? _value.referral
          : referral // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ApiKeyImplCopyWith<$Res> implements $ApiKeyCopyWith<$Res> {
  factory _$$ApiKeyImplCopyWith(
          _$ApiKeyImpl value, $Res Function(_$ApiKeyImpl) then) =
      __$$ApiKeyImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String key,
      String email,
      String tier,
      int monthlyQuota,
      int usedQuota,
      String? referral});
}

/// @nodoc
class __$$ApiKeyImplCopyWithImpl<$Res>
    extends _$ApiKeyCopyWithImpl<$Res, _$ApiKeyImpl>
    implements _$$ApiKeyImplCopyWith<$Res> {
  __$$ApiKeyImplCopyWithImpl(
      _$ApiKeyImpl _value, $Res Function(_$ApiKeyImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? key = null,
    Object? email = null,
    Object? tier = null,
    Object? monthlyQuota = null,
    Object? usedQuota = null,
    Object? referral = freezed,
  }) {
    return _then(_$ApiKeyImpl(
      key: null == key
          ? _value.key
          : key // ignore: cast_nullable_to_non_nullable
              as String,
      email: null == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String,
      tier: null == tier
          ? _value.tier
          : tier // ignore: cast_nullable_to_non_nullable
              as String,
      monthlyQuota: null == monthlyQuota
          ? _value.monthlyQuota
          : monthlyQuota // ignore: cast_nullable_to_non_nullable
              as int,
      usedQuota: null == usedQuota
          ? _value.usedQuota
          : usedQuota // ignore: cast_nullable_to_non_nullable
              as int,
      referral: freezed == referral
          ? _value.referral
          : referral // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ApiKeyImpl with DiagnosticableTreeMixin implements _ApiKey {
  const _$ApiKeyImpl(
      {required this.key,
      required this.email,
      required this.tier,
      required this.monthlyQuota,
      this.usedQuota = 0,
      this.referral});

  factory _$ApiKeyImpl.fromJson(Map<String, dynamic> json) =>
      _$$ApiKeyImplFromJson(json);

  @override
  final String key;
  @override
  final String email;
  @override
  final String tier;
  @override
  final int monthlyQuota;
  @override
  @JsonKey()
  final int usedQuota;
  @override
  final String? referral;

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'ApiKey(key: $key, email: $email, tier: $tier, monthlyQuota: $monthlyQuota, usedQuota: $usedQuota, referral: $referral)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'ApiKey'))
      ..add(DiagnosticsProperty('key', key))
      ..add(DiagnosticsProperty('email', email))
      ..add(DiagnosticsProperty('tier', tier))
      ..add(DiagnosticsProperty('monthlyQuota', monthlyQuota))
      ..add(DiagnosticsProperty('usedQuota', usedQuota))
      ..add(DiagnosticsProperty('referral', referral));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ApiKeyImpl &&
            (identical(other.key, key) || other.key == key) &&
            (identical(other.email, email) || other.email == email) &&
            (identical(other.tier, tier) || other.tier == tier) &&
            (identical(other.monthlyQuota, monthlyQuota) ||
                other.monthlyQuota == monthlyQuota) &&
            (identical(other.usedQuota, usedQuota) ||
                other.usedQuota == usedQuota) &&
            (identical(other.referral, referral) ||
                other.referral == referral));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType, key, email, tier, monthlyQuota, usedQuota, referral);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$ApiKeyImplCopyWith<_$ApiKeyImpl> get copyWith =>
      __$$ApiKeyImplCopyWithImpl<_$ApiKeyImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ApiKeyImplToJson(
      this,
    );
  }
}

abstract class _ApiKey implements ApiKey {
  const factory _ApiKey(
      {required final String key,
      required final String email,
      required final String tier,
      required final int monthlyQuota,
      final int usedQuota,
      final String? referral}) = _$ApiKeyImpl;

  factory _ApiKey.fromJson(Map<String, dynamic> json) = _$ApiKeyImpl.fromJson;

  @override
  String get key;
  @override
  String get email;
  @override
  String get tier;
  @override
  int get monthlyQuota;
  @override
  int get usedQuota;
  @override
  String? get referral;
  @override
  @JsonKey(ignore: true)
  _$$ApiKeyImplCopyWith<_$ApiKeyImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
