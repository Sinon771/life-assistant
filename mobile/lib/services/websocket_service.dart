import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'api_service.dart';
import 'notification_service.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  bool _shouldReconnect = false;
  final _listeners = <Function(Map<String, dynamic>)>[];

  bool get isConnected => _channel != null;

  void addListener(Function(Map<String, dynamic>) listener) {
    _listeners.add(listener);
  }

  void removeListener(Function(Map<String, dynamic>) listener) {
    _listeners.remove(listener);
  }

  void connect() {
    if (_channel != null) return;
    if (ApiService.token == null) return;

    _shouldReconnect = true;
    final wsUrl = '${ApiService.baseUrl.replaceFirst('http', 'ws')}/ws/${ApiService.token}';
    
    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      
      _channel!.stream.listen(
        (message) async {
          final data = jsonDecode(message);
          _notifyListeners(data);
          
          if (data['type'] == 'reminder') {
            await NotificationService.showReminderNotification(
              id: data['reminder_id'] ?? Random().nextInt(100000),
              title: data['title'] ?? '提醒',
              body: data['body'] ?? '您有一个提醒',
              reminderId: data['reminder_id'],
            );
          }
        },
        onError: (error) {
          print('WebSocket error: $error');
          _cleanup();
          _scheduleReconnect();
        },
        onDone: () {
          print('WebSocket closed');
          _cleanup();
          if (_shouldReconnect) {
            _scheduleReconnect();
          }
        },
      );

      // 心跳保活
      _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (_) {
        send({'type': 'ping', 'time': DateTime.now().millisecondsSinceEpoch});
      });
    } catch (e) {
      print('WebSocket connect error: $e');
      _scheduleReconnect();
    }
  }

  void send(Map<String, dynamic> data) {
    if (_channel != null) {
      try {
        _channel!.sink.add(jsonEncode(data));
      } catch (e) {
        print('WebSocket send error: $e');
      }
    }
  }

  void disconnect() {
    _shouldReconnect = false;
    _cleanup();
    _reconnectTimer?.cancel();
  }

  void _cleanup() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: 5), () {
      if (_shouldReconnect) {
        connect();
      }
    });
  }

  void _notifyListeners(Map<String, dynamic> data) {
    for (final listener in _listeners) {
      try {
        listener(data);
      } catch (e) {
        print('Listener error: $e');
      }
    }
  }
}
