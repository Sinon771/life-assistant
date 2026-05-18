class ChatMessage {
  final String role; // user / assistant / system
  final String content;
  final DateTime? time;
  final Map<String, dynamic>? action; // 附带操作信息

  ChatMessage({
    required this.role,
    required this.content,
    this.time,
    this.action,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'] ?? 'assistant',
      content: json['content'] ?? '',
      time: json['time'] != null ? DateTime.tryParse(json['time']) : null,
      action: json['action'],
    );
  }

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}
