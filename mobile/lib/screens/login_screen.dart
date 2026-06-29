import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/api_key.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';
import '../utils/validators.dart';
import '../widgets/loading_indicator.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailController = TextEditingController();
  bool _isLoading = false;
  String? _apiKey;
  String? _error;

  Future<void> _signup() async {
    final email = _emailController.text.trim();
    final error = Validators.emailError(email);
    if (error != null) {
      setState(() => _error = error);
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _apiKey = null;
    });

    try {
      final api = ApiService();
      final key = await api.signup(email);
      setState(() => _apiKey = key.key);
    } catch (e) {
      setState(() => _error = 'Signup failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _copyKey() {
    if (_apiKey != null) {
      Clipboard.setData(ClipboardData(text: _apiKey!));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('API key copied to clipboard')),
      );
    }
  }

  Future<void> _continueToApp() async {
    if (_apiKey == null) return;
    await ref.read(authProvider.notifier).login(
      ApiKey(
        key: _apiKey!,
        email: _emailController.text.trim(),
        tier: 'free',
        monthlyQuota: Constants.freeQuota,
      ),
    );
    if (mounted) context.go(Constants.routeHome);
  }

  Future<void> _openPricing() async {
    final uri = Uri.parse(Constants.pricingUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 48),
              Icon(
                Icons.science,
                size: 64,
                color: Constants.qmolAccent,
              ),
              const SizedBox(height: 24),
              Text(
                'Get Started with Q-Mol',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Enter your email to receive a free API key',
                style: theme.textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                decoration: InputDecoration(
                  labelText: 'Email',
                  prefixIcon: const Icon(Icons.email),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  errorText: _error,
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _isLoading ? null : _signup,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isLoading
                    ? const LoadingIndicator(size: 20)
                    : const Text('Get Free API Key'),
              ),
              if (_apiKey != null) ...[
                const SizedBox(height: 24),
                Card(
                  color: Constants.qmolAccent.withAlpha(30),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: Constants.qmolAccent.withAlpha(100)),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'Your API Key',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        SelectableText(
                          _apiKey!,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontFamily: 'monospace',
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            TextButton.icon(
                              onPressed: _copyKey,
                              icon: const Icon(Icons.copy, size: 18),
                              label: const Text('Copy'),
                            ),
                            const Spacer(),
                            ElevatedButton(
                              onPressed: _continueToApp,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Constants.qmolAccent,
                                foregroundColor: Colors.black,
                              ),
                              child: const Text('Continue'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 24),
              TextButton(
                onPressed: _openPricing,
                child: const Text('View pricing and upgrade plans'),
              ),
              const SizedBox(height: 16),
              Text(
                'By signing up, you agree to our Terms of Service and Privacy Policy.',
                style: theme.textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }
}
