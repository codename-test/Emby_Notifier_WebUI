# Emby Notifier WebUI

> 基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 的二次开发版本。

## 新增功能

### 多通道推送架构

支持多种推送通道，每个通道独立配置、独立测试，端口可关联多个通道同时推送：

| 通道类型 | 说明 |
|----------|------|
| 企业微信应用 | 通过企业微信应用 API 推送图文消息 |
| 企业微信机器人 | 通过企业微信群机器人 Webhook 推送 |
| 钉钉 | 通过钉钉机器人 Webhook 推送 |
| 飞书 | 通过飞书机器人 Webhook 推送 |
| Telegram Bot | 通过 Telegram Bot API 推送（HTML 格式） |
| Bark | 通过 Bark 推送 iOS 通知 |

### MetaTube 集成

集成 [MetaTube Server](https://metatube-community.github.io/) 作为扩展元数据源。当 TMDB 无法匹配到影片信息时，自动降级使用 MetaTube 补充数据。

**图片获取策略（逐级退避）：**

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 原始封面 | 非防盗链域名直接使用 |
| 2 | DMM/JAV321 源封面 | 搜索结果中优先选可外链源 |
| 3 | 剧照 (preview_images) | 保底方案 |

在 **系统设置** 页面配置 MetaTube Server 地址和 Token 即可启用。

### WebUI 管理界面

- **仪表盘**：系统状态概览、端口运行状态
- **端口管理**：多端口独立配置，每个端口可关联多个推送通道
- **推送通道**：添加/编辑/删除/复制通道，每个通道有独立测试按钮，支持快速复制已有通道配置
- **推送模板**：可配置推送格式模板，支持自定义变量
- **勿扰设置**：设置勿扰时间段，期间消息自动暂存到队列
- **消息队列**：查看历史消息，手动重推，清空队列
- **系统日志**：实时查看日志，按级别过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- **系统设置**：TMDB Token、MetaTube Server、翻译引擎、日志等级配置

### 推送模板系统

- **标准模板**：带封面图，完整 TMDB/MetaTube 数据（简介、评分、链接）
- **基础模板**：TMDB 失败时自动使用，无图，仅 webhook 自带数据
- **自定义模板**：用户可自由编辑模板格式

**模板规则：**
- 回退模板（基础模板）不可删除、不可在端口下拉中选择、封面图强制关闭
- 无图模板（`enable_image=0`）自动跳过 TMDB 请求，直接用 webhook 数据推送
- TMDB 失败时自动切换回退模板推送，不丢消息

### 智能识别

- 自动识别 Emby/Jellyfin 四种 Webhook 格式
- 无需手动选择服务器类型

### 数据持久化

- 所有配置存储在 SQLite 数据库
- 重启不丢失配置

### 日志系统

- 五级日志级别：DEBUG / INFO / WARNING / ERROR / CRITICAL
- 日志入库，WebUI 实时查看
- 支持按级别过滤

## 快速开始

### Docker 部署（推荐）

```bash
docker run -d \
  --name emby-notifier \
  --network host \
  -e WEB_PORT=5000 \
  -v emby_data:/data \
  codenametest/emby_notifier_webui:latest
```

或使用 docker-compose：

```bash
wget https://raw.githubusercontent.com/codename-test/Emby_Notifier_WebUI/main/docker-compose.yml
docker compose up -d
```

访问 `http://你的IP:5000`。

### 手动部署

```bash
git clone https://github.com/codename-test/Emby_Notifier_WebUI.git
cd Emby_Notifier_WebUI
pip install -r requirements.txt
python3 main.py
```

指定端口：`WEB_PORT=8080 python3 main.py`

### 配置流程

1. 访问 WebUI → **系统设置** → 填写 TMDB API Token → 保存并测试连接
2. **系统设置** → 配置 MetaTube Server（可选，扩展元数据源）
3. **推送通道** → 添加推送通道（企微应用/机器人、钉钉、飞书、Telegram、Bark）
4. **推送模板** → 选用标准或基础模板（可自定义格式）
5. **端口管理** → 添加端口，选择推送通道和推送模板，启用
6. Emby/Jellyfin 控制台 → 设置 Webhook URL：`http://你的IP:端口号/`

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEB_PORT` | 5000 | WebUI 管理界面端口 |
| `DB_PATH` | emby_notifier.db | 数据库文件路径 |
| `LOG_LEVEL` | INFO | 日志等级（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `TVDB_API_KEY` | - | TVDB API Key（可选） |
| `TMDB_IMAGE_DOMAIN` | https://image.tmdb.org | TMDB 图片域名 |

## 推送模板

### 模板变量

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
├── sender.py            # 推送发送器（多通道架构）
├── tmdb_api.py          # TMDB API
├── tvdb_api.py          # TVDB API
├── metatube_api.py      # MetaTube API（扩展元数据源）
├── translator.py        # 翻译模块（Google/百度）
├── channels/            # 多通道模块
│   ├── __init__.py      # 基类 + 工厂模式
│   ├── wechat_work_api.py   # 企业微信应用
│   ├── wechat_work_bot.py   # 企业微信机器人
│   ├── dingtalk.py          # 钉钉
│   ├── feishu.py            # 飞书
│   ├── telegram_bot.py      # Telegram Bot
│   └── bark.py              # Bark
├── my_utils.py          # 工具函数
├── log.py               # 日志模块
├── requirements.txt     # 依赖
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose（host 网络）
├── .github/workflows/   # GitHub Actions 自动构建
└── README.md
```

## 致谢

- 基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 二次开发，感谢原作者
- 扩展元数据由 [MetaTube](https://metatube-community.github.io/) 提供支持

## License

MIT
