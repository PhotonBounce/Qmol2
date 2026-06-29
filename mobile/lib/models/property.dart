import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'property.freezed.dart';
part 'property.g.dart';

@freezed
class Property with _$Property {
  const factory Property({
    required String name,
    required double? value,
    String? unit,
    @Default(0.0) double confidence,
    @Default(true) bool inDomain,
    @Default('ok') String status,
  }) = _Property;

  factory Property.fromJson(Map<String, Object?> json) => _$PropertyFromJson(json);
}
