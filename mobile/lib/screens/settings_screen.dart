import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/auth_provider.dart';
import '../services/storage_service.dart';
import '../utils/constants.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _storage = StorageService();
  String? _apiKey;
  String? _appVersion;
  String? _themeMode;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final key = await _storage.getApiKey();
    final info = await PackageInfo.fromPlatform();
    final theme = await _storage.getThemeMode() ?? 'system';
    setState(() {
      _apiKey = key;
      _appVersion = '${info.version}+${info.buildNumber}';
      _themeMode = theme;
      _loading = false;
    });
  }

  Future<void> _copyKey() async {
    if (_apiKey != null) {
      await Clipboard.setData(ClipboardData(text: _apiKey!));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('API key copied')),
        );
      }
    }
  }

  Future<void> _rotateKey() async {
    // In production, call API to rotate key
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Key rotation not yet implemented')),
      );
    }
  }

  Future<void> _setTheme(String mode) async {
    await _storage.saveThemeMode(mode);
    setState(() => _themeMode = mode);
  }

  Future<void> _clearHistory() async {
    await _storage.clearHistory();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('History cleared')),
      );
    }
  }

  Future<void> _logout() async {
    await ref.read(authProvider.notifier).logout();
    if (mounted) context.go(Constants.routeLogin);
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  String _maskKey(String key) {
    if (key.length <= 8) return '****';
    return '${key.substring(0, 4)}****${key.substring(key.length - 4)}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // API Key
          ListTile(
            leading: const Icon(Icons.key),
            title: const Text('API Key'),
            subtitle: Text(_apiKey != null ? _maskKey(_apiKey!) : 'Not logged in'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: const Icon(Icons.copy),
                  tooltip: 'Copy key',
                  onPressed: _apiKey != null ? _copyKey : null,
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Rotate key',
                  onPressed: _apiKey != null ? _rotateKey : null,
                ),
              ],
            ),
          ),
          const Divider(),

          // Theme
          ListTile(
            leading: const Icon(Icons.palette),
            title: const Text('Theme'),
            subtitle: Text(_themeMode ?? 'System default'),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'light', label: Text('Light'), icon: Icon(Icons.light_mode)),
                ButtonSegment(value: 'dark', label: Text('Dark'), icon: Icon(Icons.dark_mode)),
                ButtonSegment(value: 'system', label: Text('System'), icon: Icon(Icons.settings)),
              ],
              selected: {_themeMode ?? 'system'},
              onSelectionChanged: (selection) => _setTheme(selection.first),
            ),
          ),
          const Divider(),

          // Clear history
          ListTile(
            leading: const Icon(Icons.delete_outline),
            title: const Text('Clear History'),
            subtitle: const Text('Remove all locally saved molecules'),
            onTap: _clearHistory,
          ),
          const Divider(),

          // About
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('About Q-Mol'),
            subtitle: Text('Version $_appVersion'),
          ),
          ListTile(
            leading: const Icon(Icons.privacy_tip),
            title: const Text('Privacy Policy'),
            onTap: () => _openUrl(Constants.privacyUrl),
          ),
          ListTile(
            leading: const Icon(Icons.description),
            title: const Text('Terms of Service'),
            onTap: () => _openUrl(Constants.termsUrl),
          ),
          const Divider(),

          // Logout
          ListTile(
            leading: const Icon(Icons.logout, color: Constants.qmolError),
            title: const Text('Logout', style: TextStyle(color: Constants.qmolError)),
            onTap: _logout,
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}
