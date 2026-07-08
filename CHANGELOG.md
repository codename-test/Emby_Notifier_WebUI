# 更新日志

## v1.0.0 (2026-07-08)

### 首次发布

基于 [Emby Notifier](https://github.com/Ccccx159/Emby_Notifier) 二次开发，核心改动：

- **WebUI 管理界面** - Flask + Bootstrap 5，多页面管理
- **多端口支持** - 每端口独立线程 + 独立事件循环，支持多个 Emby/Jellyfin 服务器
- **配置持久化** - SQLite 数据库，所有配置重启不丢失
- **移除环境变量** - TMDB Token 等全部改为 WebUI 在线配置
- **勿扰模式** - 可设置时间段，消息自动暂存
- **消息队列** - 历史记录查看、手动重推

新增模块：`db.py`, `web_ui.py`, `port_manager.py`
改造模块：`main.py`, `media.py`, `sender.py`, `tmdb_api.py`
