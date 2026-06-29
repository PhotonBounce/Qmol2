import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize local notifications
  final notificationService = NotificationService();
  await notificationService.init();

  runApp(
    const ProviderScope(
      child: QmolApp(),
    ),
  );
}
