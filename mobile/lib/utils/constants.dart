import 'package:flutter/material.dart';

class Constants {
  // API
  static const String baseUrl = String.fromEnvironment(
    'QMOL_API',
    defaultValue: 'https://api.qmol.app/v1',
  );

  // Routes
  static const String routeSplash = '/';
  static const String routeLogin = '/login';
  static const String routeHome = '/home';
  static const String routeCompute = '/compute';
  static const String routeBatch = '/batch';
  static const String routeJobs = '/jobs';
  static const String routeResults = '/results';
  static const String routeMolecule = '/molecule/:smiles';
  static const String routeSettings = '/settings';

  // Colors
  static const Color qmolPrimary = Color(0xFF0A2540);
  static const Color qmolAccent = Color(0xFF00D4AA);
  static const Color qmolError = Color(0xFFFF4D4D);
  static const Color qmolWarning = Color(0xFFFFB020);
  static const Color qmolSuccess = Color(0xFF00D4AA);

  // Quota tiers
  static const int freeQuota = 500;
  static const int researchQuota = 10000;
  static const int commercialQuota = 100000;

  // Retry config
  static const int maxRetries = 3;
  static const Duration retryBaseDelay = Duration(seconds: 1);

  // Storage keys
  static const String keyApiKey = 'api_key';
  static const String keyHistory = 'history';
  static const String keyTheme = 'theme_mode';
  static const String keyOfflineQueue = 'offline_queue';

  static const String pricingUrl = 'https://qmol.app/checkout.html';
  static const String privacyUrl = 'https://qmol.app/privacy';
  static const String termsUrl = 'https://qmol.app/terms';
}
