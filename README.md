# Emby Notifier WebUI

> 基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 的二次开发版本。

## 与原版的区别

原有的 Emby Notifier 通过**环境变量**配置 TMDB Token、推送渠道等参数，不便于管理和切换。本版本进行了以下改造：

### 核心改动

| 改动项 | 原版 | 本版本 |
|--------|------|--------|
| 配置方式 | 环境变量 / 启动脚本 | **WebUI 管理界面** |
| TMDB Token | 写入环境变量 | WebUI 在线配置，保存即生效 |
| 推送渠道配置 | 环境变量逐项设置 | WebUI 表单可视化配置 |
| 多服务器支持 | ❌ 单端口 | ✅ **多端口独立配置** |
| 推送模板 | ❌ 固定格式 | ✅ **可配置模板，端口可选** |
| 配置持久化 | ❌ 重启丢失 | ✅ **SQLite 数据库持久化** |
| 勿扰模式 | ❌ 无 | ✅ **DND + 消息队列自动暂存** |
| 消息队列 | ❌ 无 | ✅ 历史记录查看、手动重推 |
| 系统日志 | ❌ 仅控制台 | ✅ **日志入库 + WebUI 查看/过滤** |
| 管理界面 | ❌ 无 | ✅ **Flask + Bootstrap 5 WebUI** |

### 新增模块

| 模块 | 说明 |
|------|------|
| `db.py` | SQLite 数据库管理，所有配置持久化 |
| `web_ui.py` | WebUI 管理界面（仪表盘/端口/勿扰/队列/日志/模板/设置） |
| `port_manager.py` | 多端口管理器，每个端口独立线程 + 独立事件循环 |
| `log.py` | 日志模块，支持 DBHandler 写入 SQLite |

### 改造模块

| 模块 | 改动说明 |
|------|----------|
| `main.py` | 移除环境变量硬编码检查，从 DB 读取日志等级 |
| `media.py` | 重写，支持多端口上下文 |
| `sender.py` | 重写，支持模板驱动推送 |
| `tmdb_api.py` | Token 改为 `db.get_system_config()` 动态读取 |

## 快速开始

### Docker 部署（推荐）

```bash
git clone https://github.com/codename-test/Emby_Notifier_WebUI.git
cd Emby_Notifier_WebUI

# 可选：修改 docker-compose.yml 中的 WEB_PORT
# 启动（host 网络模式，支持动态端口监听）
docker compose up -d
```

访问 `http://你的IP:5000`（或你自定义的端口）。

### 手动部署

```bash
git clone https://github.com/codename-test/Emby_Notifier_WebUI.git
cd Emby_Notifier_WebUI

pip install -r requirements.txt

# 默认 WebUI 端口 5000
python3 main.py

# 或指定端口
WEB_PORT=8080 python3 main.py
```

### 容器镜像构建

```bash
docker build -t emby-notifier-webui .
docker run -d --name emby-notifier --network host \
  -e WEB_PORT=5000 \
  -v emby_data:/data \
  emby-notifier-webui
```

> **说明**：容器必须使用 `--network host`，因为媒体服务监听端口在 WebUI 中动态配置，host 模式避免端口映射的复杂性。

### 配置流程

1. 访问 WebUI → **系统设置** → 填写 TMDB API Token → 保存并测试连接
2. **企业微信** → 添加企业微信配置组（Corp ID、Secret、Agent ID）
3. **推送模板** → 选用标准或简化通用模板（可自定义格式）
4. **端口管理** → 添加端口，选择企微配置组和推送模板，启用
5. Emby/Jellyfin 控制台 → 设置 Webhook URL：`http://你的IP:端口号/`

## WebUI 功能

| 页面 | 功能 |
|------|------|
| 仪表盘 | 系统状态概览、端口运行状态 |
| 端口管理 | 添加/编辑/删除端口，测试推送 |
| 勿扰设置 | 设置勿扰时间段，期间消息自动暂存 |
| 消息队列 | 查看历史消息，手动重推，清空队列 |
| 系统日志 | 实时查看日志，按级别过滤，清空 |
| 推送模板 | 管理推送格式模板（标准/简化通用） |
| 企业微信 | 管理企业微信配置组 |
| 系统设置 | TMDB Token、日志等级 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEB_PORT` | 5000 | WebUI 管理界面端口 |
| `DB_PATH` | emby_notifier.db | 数据库文件路径 |
| `LOG_LEVEL` | INFO | 日志等级（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `LOG_EXPORT` | False | 是否导出日志到文件 |
| `LOG_PATH` | /var/tmp/emby_notifier/ | 日志文件路径 |
| `TVDB_API_KEY` | - | TVDB API Key（可选） |
| `TMDB_IMAGE_DOMAIN` | https://image.tmdb.org | TMDB 图片域名 |

## 推送模板变量

在 WebUI 中可自定义模板，支持以下变量：

| 变量 | 说明 |
|------|------|
| `{type}` | 媒体类型（电影/剧集） |
| `{name}` | 媒体名称 |
| `{year}` | 发行年份 |
| `{episode}` | 季集信息（仅剧集，如 " 第1季·第10集"） |
| `{season}` | 季号 |
| `{ep_num}` | 集号 |
| `{ep_name}` | 集名 |
| `{date}` | 上映日期 |
| `{rating}` | 评分 |
| `{intro}` | 简介 |
| `{tmdb_url}` | TMDB 链接 |

## 项目结构

```
Emby_Notifier/
├── main.py              # 主程序
├── db.py                # 数据库管理
├── web_ui.py            # WebUI 界面
├── port_manager.py      # 多端口管理器
├── media.py             # 媒体处理
├── sender.py            # 推送发送器（模板驱动）
├── tmdb_api.py          # TMDB API
├── tvdb_api.py          # TVDB API
├── wxapp.py             # 企业微信
├── tgbot.py             # Telegram
├── bark.py              # Bark
├── my_utils.py          # 工具函数
├── log.py               # 日志模块
├── requirements.txt     # 依赖
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose（host 网络）
└── README.md
```

## 致谢

本项目基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 二次开发，感谢原作者。

## License

MIT
