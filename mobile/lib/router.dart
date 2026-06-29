import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/compute_screen.dart';
import 'screens/batch_screen.dart';
import 'screens/jobs_screen.dart';
import 'screens/results_screen.dart';
import 'screens/molecule_detail_screen.dart';
import 'screens/settings_screen.dart';
import 'utils/constants.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();

final GoRouter router = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: Constants.routeSplash,
  routes: [
    GoRoute(
      path: Constants.routeSplash,
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: Constants.routeLogin,
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: Constants.routeHome,
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: Constants.routeCompute,
      builder: (context, state) => const ComputeScreen(),
    ),
    GoRoute(
      path: Constants.routeBatch,
      builder: (context, state) => const BatchScreen(),
    ),
    GoRoute(
      path: Constants.routeJobs,
      builder: (context, state) => const JobsScreen(),
    ),
    GoRoute(
      path: Constants.routeResults,
      builder: (context, state) => const ResultsScreen(),
    ),
    GoRoute(
      path: '/molecule/:smiles',
      builder: (context, state) {
        final smiles = state.pathParameters['smiles'] ?? '';
        return MoleculeDetailScreen(smiles: Uri.decodeComponent(smiles));
      },
    ),
    GoRoute(
      path: Constants.routeSettings,
      builder: (context, state) => const SettingsScreen(),
    ),
  ],
);
