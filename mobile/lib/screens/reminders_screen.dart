import 'package:flutter/material.dart';
import '../models/reminder.dart';
import '../services/api_service.dart';
import '../services/local_reminder_service.dart';

class RemindersScreen extends StatefulWidget {
  const RemindersScreen({super.key});

  @override
  State<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends State<RemindersScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  List<Reminder> _reminders = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final data = await ApiService.getReminders();
    setState(() {
      _reminders = data;
      _loading = false;
    });
    // 同步活跃提醒到本地通知系统
    final active = data.where((r) => r.isActive).toList();
    await LocalReminderService.syncReminders(active);
  }

  Future<void> _complete(Reminder r) async {
    final ok = await ApiService.completeReminder(r.id);
    if (ok) {
      await LocalReminderService.cancelReminder(r.id);
      _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('"${r.title}" 已完成')),
        );
      }
    }
  }

  Future<void> _snooze(Reminder r, int minutes) async {
    final ok = await ApiService.snoozeReminder(r.id, minutes: minutes);
    if (ok) {
      await LocalReminderService.cancelReminder(r.id);
      _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已推迟$minutes分钟')),
        );
      }
    }
  }

  Future<void> _delete(Reminder r) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('删除提醒 "${r.title}"？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('删除', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final ok = await ApiService.deleteReminder(r.id);
      if (ok) {
        await LocalReminderService.cancelReminder(r.id);
        _load();
      }
    }
  }

  Widget _buildList(List<Reminder> items) {
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text('没有提醒', style: TextStyle(color: Colors.grey[500])),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: items.length,
        itemBuilder: (_, index) {
          final r = items[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: r.isActive
                    ? Theme.of(context).colorScheme.primaryContainer
                    : Colors.grey[200],
                child: Icon(
                  r.repeatRule != null ? Icons.repeat : Icons.notifications,
                  color: r.isActive
                      ? Theme.of(context).colorScheme.primary
                      : Colors.grey,
                ),
              ),
              title: Text(r.title),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.formattedTime),
                  if (r.repeatText.isNotEmpty)
                    Chip(
                      label: Text(r.repeatText, style: const TextStyle(fontSize: 11)),
                      padding: EdgeInsets.zero,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  if (r.description != null && r.description!.isNotEmpty)
                    Text(r.description!, maxLines: 2, overflow: TextOverflow.ellipsis),
                ],
              ),
              isThreeLine: r.description != null || r.repeatText.isNotEmpty,
              trailing: r.isActive
                  ? PopupMenuButton<String>(
                      onSelected: (value) {
                        switch (value) {
                          case 'complete':
                            _complete(r);
                            break;
                          case 'snooze5':
                            _snooze(r, 5);
                            break;
                          case 'snooze10':
                            _snooze(r, 10);
                            break;
                          case 'delete':
                            _delete(r);
                            break;
                        }
                      },
                      itemBuilder: (_) => [
                        const PopupMenuItem(value: 'complete', child: Text('完成')),
                        const PopupMenuItem(value: 'snooze5', child: Text('推迟5分钟')),
                        const PopupMenuItem(value: 'snooze10', child: Text('推迟10分钟')),
                        const PopupMenuItem(value: 'delete', child: Text('删除', style: TextStyle(color: Colors.red))),
                      ],
                    )
                  : IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.grey),
                      onPressed: () => _delete(r),
                    ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = _reminders.where((r) => r.isActive).toList();
    final completed = _reminders.where((r) => !r.isActive).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('我的提醒'),
        bottom: TabBar(
          controller: _tabCtrl,
          tabs: [
            Tab(text: '进行中 (${active.length})'),
            Tab(text: '已完成 (${completed.length})'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabCtrl,
              children: [
                _buildList(active),
                _buildList(completed),
              ],
            ),
    );
  }
}
