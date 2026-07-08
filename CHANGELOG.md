# 更新日志

## v5.0.0 (2025-07-08)

### 🎉 重大更新

基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 进行二次开发，全面重构架构。

#### 新增功能
- **WebUI 管理界面** - 完整的 Web 管理界面，基于 Flask + Bootstrap 5
- **多端口支持** - 支持多个 Emby/Jellyfin 服务器，每个端口独立配置
- **勿扰模式（DND）** - 设置勿扰时间段，消息自动暂存，勿扰结束后自动推送
- **配置持久化** - 所有配置保存到 SQLite 数据库，重启不丢失
- **TMDB Token 在线配置** - 通过 WebUI 配置 TMDB API Token，无需环境变量
- **TMDB Token 验证** - 保存时自动验证 Token 有效性
- **消息队列管理** - 查看历史推送记录，手动刷新待推送消息

#### 架构改进
- 移除环境变量配置依赖
- 新增 `db.py` 数据库管理模块
- 新增 `port_manager.py` 多端口管理器
- 新增 `web_ui.py` WebUI 模块
- 重写 `main.py` 启动流程
- 重写 `media.py` 媒体处理逻辑
- 重写 `sender.py` 推送发送器
- 重写 `tmdb_api.py`，改为从数据库读取 Token

#### WebUI 功能
- 仪表盘 - 查看系统状态和统计
- 端口管理 - 配置多个 Emby/Jellyfin 服务器
- 勿扰设置 - 设置勿扰时间段
- 消息队列 - 查看和管理待推送消息
- 系统设置 - 配置 TMDB API Token 等全局参数

#### 推送渠道
- 企业微信（默认启用）- 图文卡片推送
- Telegram - 支持照片和 Markdown 格式
- Bark - iOS 推送通知

### 📝 配置变更

**原版本**（环境变量配置）：
```bash
export TMDB_API_TOKEN="your_token"
export WECHAT_CORP_ID="your_corp_id"
# ... 更多环境变量
```

**v5.0 版本**（WebUI 配置）：
- 所有配置通过 WebUI 完成
- 配置保存到数据库
- 无需修改环境变量或启动脚本

### 🚀 部署方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
./start.sh

# 访问 WebUI
http://你的服务器IP:5000
```

### ⚠️ 升级注意事项

1. **配置迁移**：v5.0 不再使用环境变量，需要在 WebUI 中重新配置
2. **数据库初始化**：首次启动会自动创建数据库
3. **端口变更**：WebUI 默认端口为 5000，可通过 `WEB_PORT` 环境变量修改
