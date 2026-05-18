import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'services/api_service.dart';
import 'services/notification_service.dart';
import 'services/websocket_service.dart';
import 'services/local_reminder_service.dart';
import 'services/notification_handler.dart';
import 'screens/login_screen.dart';
import 'screens/chat_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  
  await ApiService.init();
  await NotificationService.init();
  await LocalReminderService.init();
  
  if (ApiService.isLoggedIn) {
    WebSocketService().connect();
  }
  
  runApp(const LifeAssistantApp());
}

class LifeAssistantApp extends StatelessWidget {
  const LifeAssistantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: NotificationHandler.navigatorKey,
      title: '生活助手',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4A90D9),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'NotoSansSC',
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4A90D9),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        fontFamily: 'NotoSansSC',
      ),
      home: ApiService.isLoggedIn ? const ChatScreen() : const LoginScreen(),
    );
  }
}
