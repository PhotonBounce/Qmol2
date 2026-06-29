import 'package:flutter/material.dart';

class Validators {
  static final RegExp _smilesPattern = RegExp(
    r'^[A-Za-z0-9\.\+\-\=\#\$\:\(\)\[\]\*@\\/%~]{1,}$',
  );

  static bool isValidSmiles(String smiles) {
    if (smiles.trim().isEmpty) return false;
    if (smiles.length > 1000) return false;
    return _smilesPattern.hasMatch(smiles.trim());
  }

  static bool isValidEmail(String email) {
    if (email.trim().isEmpty) return false;
    final pattern = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );
    return pattern.hasMatch(email.trim());
  }

  static String? smilesError(String? smiles) {
    if (smiles == null || smiles.trim().isEmpty) {
      return 'SMILES string is required';
    }
    if (!isValidSmiles(smiles)) {
      return 'Invalid SMILES format';
    }
    return null;
  }

  static String? emailError(String? email) {
    if (email == null || email.trim().isEmpty) {
      return 'Email is required';
    }
    if (!isValidEmail(email)) {
      return 'Invalid email format';
    }
    return null;
  }

  static List<String> parseMultiSmiles(String input) {
    return input
        .split(RegExp(r'[\n\r,;]+'))
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }
}
