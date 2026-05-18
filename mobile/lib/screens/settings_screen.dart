import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _serverCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _serverCtrl.text = ApiService.baseUrl;
  }

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('退出登录'),
        content: const Text('确定要退出当前账号吗？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('退出')),
        ],
      ),
    );

    if (confirm == true) {
      await ApiService.clearAuth();
      WebSocketService().disconnect();
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const LoginScreen()),
          (route) => false,
        );
      }
    }
  }

  Future<void> _saveServer() async {
    final url = _serverCtrl.text.trim();
    if (url.isNotEmpty) {
      await ApiService.setBaseUrl(url);
      WebSocketService().disconnect();
      WebSocketService().connect();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('服务器地址已更新')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        children: [
          // 账号信息
          ListTile(
            leading: CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primary,
              child: Text(
                (ApiService.username ?? 'U')[0].toUpperCase(),
                style: const TextStyle(color: Colors.white),
              ),
            ),
            title: Text(ApiService.username ?? '未知用户'),
            subtitle: Text('用户ID: ${ApiService.userId ?? '-'}'),
          ),
          const Divider(),
          // 服务器设置
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('服务器地址', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                TextField(
                  controller: _serverCtrl,
                  decoration: InputDecoration(
                    hintText: 'http://your-server-ip:8000',
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.save),
                      onPressed: _saveServer,
                    ),
                    border: const OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          const Divider(),
          // WebSocket状态
          ListTile(
            leading: Icon(
              Icons.circle,
              color: WebSocketService().isConnected ? Colors.green : Colors.grey,
            ),
            title: const Text('实时推送'),
            subtitle: Text(WebSocketService().isConnected ? '已连接' : '未连接'),
            trailing: TextButton(
              onPressed: () {
                WebSocketService().connect();
                setState(() {});
              },
              child: const Text('重连'),
            ),
          ),
          const Divider(),
          // 关于
          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('关于'),
            subtitle: Text('生活助手 v1.0.0'),
          ),
          const SizedBox(height: 32),
          // 退出登录
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: ElevatedButton(
              onPressed: _logout,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
                minimumSize: const Size(double.infinity, 48),
              ),
              child: const Text('退出登录'),
            ),
          ),
        ],
      ),
    );
  }
}
