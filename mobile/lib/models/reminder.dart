class Reminder {
  final int id;
  final String title;
  final String? description;
  final DateTime triggerAt;
  final String? repeatRule;
  final bool isActive;
  final bool isCompleted;
  final int snoozeCount;
  final DateTime createdAt;

  Reminder({
    required this.id,
    required this.title,
    this.description,
    required this.triggerAt,
    this.repeatRule,
    required this.isActive,
    required this.isCompleted,
    required this.snoozeCount,
    required this.createdAt,
  });

  factory Reminder.fromJson(Map<String, dynamic> json) {
    return Reminder(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      triggerAt: DateTime.parse(json['trigger_at']),
      repeatRule: json['repeat_rule'],
      isActive: json['is_active'] ?? false,
      isCompleted: json['is_completed'] ?? false,
      snoozeCount: json['snooze_count'] ?? 0,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  String get repeatText {
    switch (repeatRule) {
      case 'daily':
        return '每天';
      case 'weekly':
        return '每周';
      case 'weekdays':
        return '工作日';
      case 'weekends':
        return '周末';
      default:
        return '';
    }
  }

  String get formattedTime {
    final now = DateTime.now();
    final local = triggerAt.toLocal();
    if (local.year == now.year && local.month == now.month && local.day == now.day) {
      return '今天 ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
    }
    return '${local.month}月${local.day}日 ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }
}
