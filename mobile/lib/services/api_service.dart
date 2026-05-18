import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/chat_message.dart';
import '../models/reminder.dart';

class ApiService {
  // 修改为实际服务器地址
  static String baseUrl = 'http://YOUR_SERVER_IP:8000';
  
  static String? _token;
  static int? _userId;
  static String? _username;

  static String? get token => _token;
  static int? get userId => _userId;
  static String? get username => _username;
  static bool get isLoggedIn => _token != null;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('token');
    _userId = prefs.getInt('user_id');
    _username = prefs.getString('username');
    final savedUrl = prefs.getString('base_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      baseUrl = savedUrl;
    }
  }

  static Future<void> setBaseUrl(String url) async {
    baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', url);
  }

  static Future<void> saveAuth(String token, int userId, String username) async {
    _token = token;
    _userId = userId;
    _username = username;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    await prefs.setInt('user_id', userId);
    await prefs.setString('username', username);
  }

  static Future<void> clearAuth() async {
    _token = null;
    _userId = null;
    _username = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('user_id');
    await prefs.remove('username');
  }

  static Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  // ========== Auth ==========
  static Future<Map<String, dynamic>> register(String username, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = jsonDecode(resp.body);
    if (resp.statusCode == 200) {
      await saveAuth(data['token'], data['user_id'], data['username']);
    }
    return {'success': resp.statusCode == 200, 'data': data};
  }

  static Future<Map<String, dynamic>> login(String username, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = jsonDecode(resp.body);
    if (resp.statusCode == 200) {
      await saveAuth(data['token'], data['user_id'], data['username']);
    }
    return {'success': resp.statusCode == 200, 'data': data};
  }

  // ========== Chat ==========
  static Future<Map<String, dynamic>> sendMessage(String message, {String timezone = 'Asia/Shanghai'}) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/chat'),
      headers: _headers,
      body: jsonEncode({'message': message, 'timezone': timezone}),
    );
    final data = jsonDecode(resp.body);
    return {'success': resp.statusCode == 200, 'data': data};
  }

  static Future<List<ChatMessage>> getChatHistory({int limit = 50}) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/chat/history?limit=$limit'),
      headers: _headers,
    );
    if (resp.statusCode == 200) {
      final List data = jsonDecode(resp.body);
      return data.map((e) => ChatMessage.fromJson(e)).toList();
    }
    return [];
  }

  // ========== Reminders ==========
  static Future<List<Reminder>> getReminders({bool activeOnly = false}) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/reminders?active_only=$activeOnly'),
      headers: _headers,
    );
    if (resp.statusCode == 200) {
      final List data = jsonDecode(resp.body);
      return data.map((e) => Reminder.fromJson(e)).toList();
    }
    return [];
  }

  static Future<bool> snoozeReminder(int id, {int minutes = 10}) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/reminders/$id/snooze?minutes=$minutes'),
      headers: _headers,
    );
    return resp.statusCode == 200;
  }

  static Future<bool> completeReminder(int id) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/reminders/$id/complete'),
      headers: _headers,
    );
    return resp.statusCode == 200;
  }

  static Future<bool> deleteReminder(int id) async {
    final resp = await http.delete(
      Uri.parse('$baseUrl/reminders/$id'),
      headers: _headers,
    );
    return resp.statusCode == 200;
  }

  // ========== Health ==========
  static Future<bool> checkHealth() async {
    try {
      final resp = await http.get(Uri.parse('$baseUrl/health')).timeout(Duration(seconds: 5));
      return resp.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
