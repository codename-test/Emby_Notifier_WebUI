# Emby Notifier WebUI

> 基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 的二次开发版本。

## 与原版的区别

原有的 Emby Notifier 通过**环境变量**配置 TMDB Token、推送渠道等参数，不便于管理和切换。本版本进行了以下改造：

### 🔧 核心改动

| 改动项 | 原版 | 本版本 |
|--------|------|--------|
| 配置方式 | 环境变量 / 启动脚本 | **WebUI 管理界面** |
| TMDB Token | 写入环境变量 | WebUI 在线配置，保存即生效 |
| 推送渠道配置 | 环境变量逐项设置 | WebUI 表单可视化配置 |
| 多服务器支持 | ❌ 单端口 | ✅ **多端口独立配置** |
| 配置持久化 | ❌ 重启丢失 | ✅ **SQLite 数据库持久化** |
| 勿扰模式 | ❌ 无 | ✅ **DND + 消息队列自动暂存** |
| 消息队列 | ❌ 无 | ✅ 历史记录查看、手动重推 |
| 管理界面 | ❌ 无 | ✅ **Flask + Bootstrap 5 WebUI** |

### 📦 新增模块

| 模块 | 说明 |
|------|------|
| `db.py` | SQLite 数据库管理，所有配置持久化 |
| `web_ui.py` | WebUI 管理界面（仪表盘/端口管理/勿扰/队列/系统设置） |
| `port_manager.py` | 多端口管理器，每个端口独立线程 + 独立事件循环 |

### 🔄 改造模块

| 模块 | 改动说明 |
|------|----------|
| `main.py` | 移除 `check_tmdb()` 环境变量检查，启动流程简化 |
| `media.py` | 重写，支持多端口上下文 |
| `sender.py` | 重写，支持多渠道配置动态加载 |
| `tmdb_api.py` | Token 改为 `db.get_system_config()` 动态读取 |

## 支持的推送渠道

- **企业微信** - 图文卡片推送
- **Telegram** - 照片 + Markdown 格式
- **Bark** - iOS 推送通知

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动

```bash
# 默认 WebUI 端口 5000
./start.sh

# 指定端口
WEB_PORT=8080 ./start.sh
```

### 3. 访问 WebUI

```
http://你的IP:5000
```

### 4. 配置流程

1. **系统设置** → 填写 TMDB API Token（必填），保存并测试连接
2. **端口管理** → 添加端口，配置服务器类型和推送渠道
3. **Emby/Jellyfin** → 控制台配置 Webhook URL：`http://你的IP:端口号/`

## WebUI 功能

| 页面 | 功能 |
|------|------|
| 仪表盘 | 系统状态概览、端口运行状态 |
| 端口管理 | 添加/删除/启停端口，配置推送渠道，测试推送 |
| 勿扰设置 | 设置勿扰时间段，期间消息自动暂存 |
| 消息队列 | 查看历史消息，手动重推，清空队列 |
| 系统设置 | 配置 TMDB/ TVDB API Token，TMDB 图片域名 |

## 项目结构

```
Emby_Notifier/
├── main.py              # 主程序
├── db.py                # 数据库管理 ✨
├── web_ui.py            # WebUI 界面 ✨
├── port_manager.py      # 多端口管理器 ✨
├── media.py             # 媒体处理（改造）
├── sender.py            # 推送发送器（改造）
├── tmdb_api.py          # TMDB API（改造）
├── tvdb_api.py          # TVDB API
├── wxapp.py             # 企业微信
├── tgbot.py             # Telegram
├── bark.py              # Bark
├── my_utils.py          # 工具函数
├── log.py               # 日志模块
├── start.sh             # 启动脚本 ✨
├── requirements.txt     # 依赖
├── docker-compose.yml   # Docker Compose
├── dockerfile           # Docker x86_64
├── dockerfile-aarch64   # Docker ARM64
└── doc/                 # 配置截图
```

## 致谢

本项目基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 二次开发，感谢原作者。

## License

MIT
