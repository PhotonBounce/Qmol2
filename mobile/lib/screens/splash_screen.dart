import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../utils/constants.dart';
import '../widgets/loading_indicator.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;

    final authState = ref.read(authProvider);
    authState.whenData((state) {
      if (state == AuthState.authenticated) {
        context.go(Constants.routeHome);
      } else {
        context.go(Constants.routeLogin);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Constants.qmolPrimary,
              theme.colorScheme.surface,
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              Icon(
                Icons.science,
                size: 80,
                color: Constants.qmolAccent,
              ),
              const SizedBox(height: 24),
              Text(
                'Q-Mol',
                style: theme.textTheme.displayMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 2,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Molecular Descriptors & Cheminformatics',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: Colors.white.withAlpha(200),
                ),
              ),
              const Spacer(),
              const LoadingIndicator(
                message: 'Checking credentials...',
                size: 32,
              ),
              const SizedBox(height: 48),
            ],
          ),
        ),
      ),
    );
  }
}
