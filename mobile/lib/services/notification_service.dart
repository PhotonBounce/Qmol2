import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notifications.initialize(initSettings);
    _initialized = true;
  }

  Future<void> showJobComplete(String jobId, int nProcessed) async {
    const androidDetails = AndroidNotificationDetails(
      'qmol_jobs_channel',
      'Q-Mol Job Notifications',
      channelDescription: 'Notifications for Q-Mol batch job completion',
      importance: Importance.high,
      priority: Priority.high,
      showWhen: true,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      jobId.hashCode,
      'Q-Mol Batch Complete',
      'Job $jobId finished processing $nProcessed molecules',
      details,
    );
  }

  Future<void> showJobFailed(String jobId, String error) async {
    const androidDetails = AndroidNotificationDetails(
      'qmol_jobs_channel',
      'Q-Mol Job Notifications',
      channelDescription: 'Notifications for Q-Mol batch job failures',
      importance: Importance.high,
      priority: Priority.high,
      showWhen: true,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      jobId.hashCode,
      'Q-Mol Batch Failed',
      'Job $jobId failed: $error',
      details,
    );
  }

  Future<void> showNotification({
    required String title,
    required String body,
    int id = 0,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'qmol_general_channel',
      'Q-Mol General',
      channelDescription: 'General Q-Mol notifications',
      importance: Importance.defaultImportance,
      priority: Priority.defaultPriority,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(id, title, body, details);
  }
}
