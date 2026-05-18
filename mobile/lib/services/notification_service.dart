import 'dart:math';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'notification_handler.dart';

class NotificationService {
  static final FlutterLocalNotificationsPlugin notifications =
      FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(android: androidSettings, iOS: iosSettings);

    await notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: NotificationHandler.handleNotificationResponse,
    );

    // Android 13+ 需要请求通知权限
    final platform = notifications.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    if (platform != null) {
      await platform.requestNotificationsPermission();
    }

    _initialized = true;
  }

  static Future<void> showReminderNotification({
    required int id,
    required String title,
    required String body,
    int? reminderId,
  }) async {
    final androidDetails = AndroidNotificationDetails(
      'reminder_channel',
      '提醒通知',
      channelDescription: '生活助手提醒',
      importance: Importance.max,
      priority: Priority.high,
      ticker: '提醒',
      showWhen: true,
      autoCancel: false,
      ongoing: true,
      fullScreenIntent: true,
      category: AndroidNotificationCategory.reminder,
      actions: <AndroidNotificationAction>[
        AndroidNotificationAction(
          'complete',
          '完成',
          showsUserInterface: false,
        ),
        AndroidNotificationAction(
          'snooze_5',
          '推迟5分钟',
          showsUserInterface: false,
        ),
        AndroidNotificationAction(
          'snooze_10',
          '推迟10分钟',
          showsUserInterface: false,
        ),
      ],
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(android: androidDetails, iOS: iosDetails);

    await notifications.show(
      id,
      title,
      body,
      details,
      payload: reminderId?.toString(),
    );
  }

  static Future<void> showSimpleNotification({
    required String title,
    required String body,
  }) async {
    final androidDetails = AndroidNotificationDetails(
      'general_channel',
      '一般通知',
      channelDescription: '一般消息通知',
      importance: Importance.defaultImportance,
      priority: Priority.defaultPriority,
    );

    const iosDetails = DarwinNotificationDetails();
    final details = NotificationDetails(android: androidDetails, iOS: iosDetails);

    await notifications.show(
      Random().nextInt(100000),
      title,
      body,
      details,
    );
  }

  static Future<void> cancel(int id) async {
    await notifications.cancel(id);
  }

  static Future<void> cancelAll() async {
    await notifications.cancelAll();
  }
}
