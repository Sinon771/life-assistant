# 生活助手 - AI聊天与智能提醒

一款通过自然语言对话来管理提醒的生活助手APP。支持精确时间解析、重复提醒、推迟任务，接入大语言模型实现智能交互。

## 功能特性

- **AI聊天**：接入硅基流动 / Kimi 大模型，支持自然语言对话
- **智能提醒**：
  - 精确时间解析："两分钟后提醒我喝水"
  - 重复提醒："每天早上8点提醒我喝水"
  - 推迟任务：到时间了说"推迟10分钟"
  - 取消任务："取消刚才的提醒"
- **实时推送**：WebSocket长连接 + Android本地通知，无需翻墙
- **轻量后端**：FastAPI + SQLite，适合2核1G服务器

## 技术架构

```
┌─────────────────────────────────┐
│         Flutter Android         │
│  ┌─────────┐    ┌────────────┐ │
│  │ 聊天界面 │◄──►│ 本地通知系统 │ │  ← App被杀也能响
│  └────┬────┘    └─────┬──────┘ │
│       │               │        │
│  ┌────┴────┐    ┌─────┴──────┐ │
│  │ WebSocket│    │ 本地闹钟调度 │ │
│  └────┬────┘    └────────────┘ │
└───────┼─────────────────────────┘
        │ HTTP / WebSocket
        ▼
┌─────────────────────────────────┐
│      新加坡服务器 :8000          │
│  FastAPI + SQLite + APScheduler │
│       ↓ 调用大模型API            │
│  硅基流动 / Kimi                │
└─────────────────────────────────┘
```

**双重通知保障：**
1. **实时推送**：WebSocket长连接，App前台时即时送达
2. **本地闹钟**：每次创建提醒同步到手机本地通知系统，即使App被杀死、服务器宕机，手机系统也会在准确时间弹出通知

## 快速开始

### 1. 后端部署（新加坡服务器）

```bash
# 克隆项目
cd life-assistant

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的硅基流动 API Key
# SILICONFLOW_API_KEY=sk-xxxxxxxx

# 启动（需要安装Docker和docker-compose）
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

**手动启动（无Docker）：**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量后
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 移动端构建（Flutter）

**环境要求：** Flutter 3.16+，Android SDK

```bash
cd mobile

# 修改服务器地址
# 编辑 lib/services/api_service.dart，将 baseUrl 改为你的服务器IP
# static String baseUrl = 'http://YOUR_SERVER_IP:8000';

# 安装依赖
flutter pub get

# 构建 APK
flutter build apk --release

# APK 输出路径
# build/app/outputs/flutter-apk/app-release.apk
```

### 3. 防火墙配置

确保服务器开放 8000 端口：

```bash
# Ubuntu/Debian (ufw)
ufw allow 8000/tcp

# 或使用 cloud provider 的安全组控制台开放 TCP 8000
```

## API Key 获取

### 硅基流动（推荐，国内直连）

1. 访问 https://cloud.siliconflow.cn
2. 注册账号，创建 API Key
3. 模型推荐：`deepseek-ai/DeepSeek-V2.5`（便宜好用）
4. 将 Key 填入 `.env` 的 `SILICONFLOW_API_KEY`

### Kimi（可选）

1. 访问 https://platform.moonshot.cn
2. 注册账号，创建 API Key
3. 修改 `docker-compose.yml`：
   - `LLM_PROVIDER=kimi`
   - `KIMI_API_KEY=your-key`

## 使用指南

### 对话示例

| 你说 | 效果 |
|------|------|
| "两分钟后提醒我喝水" | 创建2分钟后的单次提醒 |
| "每天早上8点提醒我喝水" | 创建每天重复的提醒 |
| "每周一早上9点开会" | 创建每周一重复的提醒 |
| "工作日每天早上打卡" | 周一到周五重复 |
| "推迟10分钟" | 将最近一个活跃提醒推迟10分钟 |
| "取消刚才的提醒" | 取消最近创建的提醒 |
| "我有什么待办" | 列出所有活跃提醒 |

### 通知行为

提醒到达时，通知栏会显示：
- **完成**：标记提醒为已完成
- **推迟5分钟**：再响一次
- **推迟10分钟**：再响一次

## 系统要求

| 组件 | 最低要求 |
|------|---------|
| 服务器 | 2核1G，任意Linux |
| Android | Android 8.0 (API 26) 及以上 |
| 网络 | 服务器需有公网IP |

## 项目结构

```
life-assistant/
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── main.py        # 入口
│   │   ├── models.py      # 数据模型
│   │   ├── services/
│   │   │   ├── llm.py     # AI服务
│   │   │   ├── scheduler.py # 定时调度
│   │   │   └── push.py    # WebSocket推送
│   │   └── routers/       # API路由
│   ├── Dockerfile
│   └── requirements.txt
├── mobile/                # Flutter 安卓端
│   ├── lib/
│   │   ├── screens/       # 页面
│   │   ├── services/      # API/WS/通知
│   │   └── models/        # 数据模型
│   └── pubspec.yaml
└── docker-compose.yml
```

## 性能优化建议（2核1G服务器）

1. **SQLite足够**：单用户/小团队使用SQLite性能完全足够
2. **单worker**：Dockerfile已设置 `--workers 1`，节省内存
3. **日志轮转**：docker-compose已配置日志限制（10MB×3个文件）
4. **如需更高并发**：可改用 PostgreSQL + Gunicorn多worker

## 常见问题

**Q: 通知不弹出？**
A: 
1. 检查 Android 13+ 的通知权限是否已授予。设置 → 应用 → 生活助手 → 通知 → 允许。
2. 检查是否开启了"精确闹钟"权限（Android 12+）。设置 → 应用 → 生活助手 → 闹钟和提醒 → 允许。
3. 某些国产系统（小米/华为/OPPO）需要将App加入电池优化白名单。

**Q: WebSocket断开后不自动重连？**
A: App在后台可能被系统限制。可尝试：设置 → 电池 → 允许后台活动。

**Q: 服务器在国内访问慢？**
A: 硅基流动API在国内有节点，新加坡服务器直连应该很快。如慢可换香港/日本服务器。

**Q: 如何备份数据？**
A: SQLite数据库在 `data/life_assistant.db`，直接复制该文件即可备份。

## License

MIT
