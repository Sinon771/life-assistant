import 'package:flutter/material.dart';
import 'api_service.dart';
import 'notification_service.dart';

class NotificationHandler {
  static final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  static void handleNotificationResponse(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;

    final reminderId = int.tryParse(payload);
    if (reminderId == null) return;

    switch (response.actionId) {
      case 'complete':
        _complete(reminderId);
        break;
      case 'snooze_5':
      case 'snooze5':
        _snooze(reminderId, 5);
        break;
      case 'snooze_10':
      case 'snooze10':
        _snooze(reminderId, 10);
        break;
      default:
        // 点击通知主体，跳转到App
        break;
    }
  }

  static void _complete(int reminderId) async {
    final ok = await ApiService.completeReminder(reminderId);
    if (ok) {
      _showSnackBar('提醒已完成');
    }
  }

  static void _snooze(int reminderId, int minutes) async {
    final ok = await ApiService.snoozeReminder(reminderId, minutes: minutes);
    if (ok) {
      _showSnackBar('已推迟$minutes分钟');
    }
  }

  static void _showSnackBar(String message) {
    final context = navigatorKey.currentContext;
    if (context != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    }
  }
}
