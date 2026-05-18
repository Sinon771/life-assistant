import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz_data;
import '../models/reminder.dart';
import 'notification_service.dart';

class LocalReminderService {
  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;
    tz_data.initializeTimeZones();
    _initialized = true;
  }

  static Future<void> scheduleReminder(Reminder reminder) async {
    await init();

    final scheduledDate = tz.TZDateTime.from(reminder.triggerAt, tz.local);
    if (scheduledDate.isBefore(DateTime.now())) return;

    final androidDetails = AndroidNotificationDetails(
      'reminder_channel',
      '提醒通知',
      channelDescription: '生活助手提醒',
      importance: Importance.max,
      priority: Priority.high,
      showWhen: true,
      autoCancel: false,
      ongoing: true,
      fullScreenIntent: true,
      category: AndroidNotificationCategory.reminder,
      actions: const <AndroidNotificationAction>[
        AndroidNotificationAction('complete', '完成', showsUserInterface: false),
        AndroidNotificationAction('snooze_5', '推迟5分钟', showsUserInterface: false),
        AndroidNotificationAction('snooze_10', '推迟10分钟', showsUserInterface: false),
      ],
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(android: androidDetails, iOS: iosDetails);

    // 重复规则映射到本地通知的重复模式
    DateTimeComponents? repeat;
    if (reminder.repeatRule == 'daily') {
      repeat = DateTimeComponents.time;
    } else if (reminder.repeatRule == 'weekly') {
      repeat = DateTimeComponents.dayOfWeekAndTime;
    }

    await NotificationService.notifications.zonedSchedule(
      reminder.id,
      reminder.title,
      reminder.description ?? '您有一个提醒',
      scheduledDate,
      details,
      payload: reminder.id.toString(),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      matchDateTimeComponents: repeat,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
    );
  }

  static Future<void> cancelReminder(int id) async {
    await NotificationService.notifications.cancel(id);
  }

  static Future<void> cancelAll() async {
    await NotificationService.notifications.cancelAll();
  }

  static Future<void> syncReminders(List<Reminder> reminders) async {
    await cancelAll();
    for (final r in reminders.where((r) => r.isActive)) {
      await scheduleReminder(r);
    }
  }
}
