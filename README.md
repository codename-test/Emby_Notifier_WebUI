# Emby Notifier

> 基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 的二次开发版本，新增 WebUI 管理界面、多端口支持和勿扰模式等功能。

## 🎉 v5.0.0 重大更新

### 全新特性
- **WebUI 管理界面** - 完整的 Web 管理界面，无需修改配置文件
- **多端口支持** - 支持多个 Emby/Jellyfin 服务器，每个端口独立配置
- **勿扰模式** - 设置勿扰时间段，消息自动暂存，勿扰结束后自动推送
- **配置持久化** - 所有配置保存到数据库，重启不丢失
- **移除环境变量** - TMDB API Token 等配置通过 WebUI 集中管理

## 支持的推送渠道

- **企业微信**（推荐）- 图文卡片推送，支持 Markdown 格式
- **Telegram** - 支持照片和 Markdown 格式
- **Bark** - iOS 推送通知

## 快速开始

### 1. 部署服务

#### 方式一：直接运行
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（默认端口 5000）
./start.sh

# 或指定 WebUI 端口
WEB_PORT=8080 ./start.sh
```

#### 方式二：Docker 部署
```bash
docker-compose up -d
```

### 2. 访问 WebUI

打开浏览器访问：`http://你的服务器IP:端口`

例如：`http://192.168.1.100:5000`

### 3. 配置 TMDB API Token

1. 点击左侧菜单的【系统设置】
2. 填写 TMDB API Token（必填）
   - 获取地址：https://www.themoviedb.org/settings/api
3. （可选）填写 TVDB API Key
   - 获取地址：https://www.thetvdb.com/api-information
4. 点击【保存配置】
5. 点击【测试 TMDB 连接】验证配置

### 4. 配置端口和推送渠道

1. 点击【端口管理】
2. 点击【添加端口】
3. 填写：
   - 端口号（如 8001）
   - 服务器名称（如 "我的 Emby"）
   - 服务器类型（Emby/Jellyfin）
4. 点击【配置】按钮，设置推送渠道：
   - 企业微信（推荐）
   - Telegram
   - Bark（iOS 推送）
5. 保存配置

### 5. 配置 Emby/Jellyfin Webhook

在你的 Emby 或 Jellyfin 控制台中：
- **URL**: `http://你的服务器IP:端口号/`
- **事件类型**: 选择 `library.new`（媒体库新增）
- **请求格式**: `application/json`

### 6. 测试推送

1. 在端口管理页面，点击【测试推送】按钮
2. 系统会发送测试消息到所有已启用的推送渠道
3. 检查是否收到通知

## 功能特性

### 多端口支持
- 每个端口独立配置
- 支持多个 Emby/Jellyfin 服务器
- 端口间推送配置互不影响

### 推送渠道

#### 企业微信
- 图文卡片推送
- 支持 Markdown 格式
- 需要创建企业微信应用

#### Telegram
- 支持照片推送
- 支持 Markdown 格式
- 需要创建 Telegram Bot

#### Bark
- iOS 推送通知
- 简单易用
- 需要安装 Bark App

### 勿扰模式
- 全局勿扰时间设置
- 勿扰期间消息自动暂存
- 勿扰结束后自动推送

### 消息队列
- 查看历史推送记录
- 手动刷新待推送消息
- 支持删除队列消息

## 系统要求

- Python 3.8+
- Emby Server 4.8.0.80 或更新版本（或 Jellyfin Server）
- TMDB API Token（必须）

## 项目结构

```
Emby_Notifier/
├── main.py              # 主程序
├── db.py                # 数据库管理
├── web_ui.py            # WebUI 界面
├── port_manager.py      # 多端口管理器
├── media.py             # 媒体处理逻辑
├── sender.py            # 推送发送器
├── tmdb_api.py          # TMDB API
├── tvdb_api.py          # TVDB API
├── wxapp.py             # 企业微信推送
├── tgbot.py             # Telegram 推送
├── bark.py              # Bark 推送
├── my_utils.py          # 工具函数
├── log.py               # 日志模块
├── start.sh             # 启动脚本
├── requirements.txt     # Python 依赖
├── docker-compose.yml   # Docker 配置
├── dockerfile           # Docker 配置
└── doc/                 # 文档和图片
```

## 常用命令

```bash
# 查看日志
tail -f emby.log

# 查看进程
ps aux | grep emby_notifier

# 停止服务
pkill -f emby_notifier

# 重启服务
pkill -f emby_notifier && ./start.sh
```

## 故障排查

### 问题：无法访问 WebUI
- 检查服务是否运行：`ps aux | grep emby_notifier`
- 检查端口是否监听：`netstat -tlnp | grep 5000`
- 查看日志：`tail emby.log`

### 问题：TMDB Token 验证失败
- 确认 Token 格式正确（应该是长字符串）
- 检查网络连接：`curl -I https://api.themoviedb.org`
- 重新获取 Token：https://www.themoviedb.org/settings/api

### 问题：收不到推送通知
- 检查推送渠道是否启用
- 检查渠道配置是否正确
- 使用【测试推送】功能验证
- 查看日志中的错误信息

## 修订版本

| 版本 | 日期 | 修订说明 |
| ----- | ----- | ----- |
| v5.0.0 | 2025.07.08 | <li>1. 新增 WebUI 管理界面；</li><li>2. 支持多端口独立配置；</li><li>3. 新增勿扰模式（DND）；</li><li>4. 配置持久化到数据库；</li><li>5. 移除环境变量配置依赖；</li><li>6. TMDB Token 在线配置和验证</li> |

## 致谢

本项目基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 进行二次开发，感谢原作者的贡献。

## License

MIT License
