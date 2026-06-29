import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:path_provider/path_provider.dart';

import '../models/molecule.dart';
import '../utils/constants.dart';

class StorageService {
  static const _secureOptions = AndroidOptions(
    encryptedSharedPreferences: true,
  );
  final FlutterSecureStorage _secureStorage;
  SharedPreferences? _prefs;

  StorageService({FlutterSecureStorage? secureStorage})
      : _secureStorage = secureStorage ??
            const FlutterSecureStorage(aOptions: _secureOptions);

  Future<SharedPreferences> get _preferences async {
    _prefs ??= await SharedPreferences.getInstance();
    return _prefs!;
  }

  Future<void> saveApiKey(String key) async {
    await _secureStorage.write(key: Constants.keyApiKey, value: key);
  }

  Future<String?> getApiKey() async {
    return _secureStorage.read(key: Constants.keyApiKey);
  }

  Future<void> deleteApiKey() async {
    await _secureStorage.delete(key: Constants.keyApiKey);
  }

  Future<void> saveHistory(List<Molecule> history) async {
    final prefs = await _preferences;
    final jsonList = history
        .map((m) => jsonEncode(m.toJson()))
        .toList();
    await prefs.setStringList(Constants.keyHistory, jsonList);
  }

  Future<List<Molecule>> getHistory() async {
    final prefs = await _preferences;
    final jsonList = prefs.getStringList(Constants.keyHistory) ?? [];
    return jsonList
        .map((s) => Molecule.fromJson(jsonDecode(s) as Map<String, dynamic>))
        .toList();
  }

  Future<void> clearHistory() async {
    final prefs = await _preferences;
    await prefs.remove(Constants.keyHistory);
  }

  Future<void> saveThemeMode(String mode) async {
    final prefs = await _preferences;
    await prefs.setString(Constants.keyTheme, mode);
  }

  Future<String?> getThemeMode() async {
    final prefs = await _preferences;
    return prefs.getString(Constants.keyTheme);
  }

  Future<String> getLocalPath() async {
    final dir = await getApplicationDocumentsDirectory();
    return dir.path;
  }

  Future<File> saveToFile(String fileName, String content) async {
    final path = await getLocalPath();
    final file = File('$path/$fileName');
    return file.writeAsString(content);
  }
}
