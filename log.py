#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import logging, colorlog, datetime, re, os

'''
Loggers：记录器，提供应用程序代码能直接使用的接口；
Handlers：处理器，将记录器产生的日志发送至目的地；
Filters：过滤器，提供更好的粒度控制，决定哪些日志会被输出；
Formatters：格式化器，设置日志内容的组成结构和消息字段。
'''


'''日志颜色配置'''
log_colors_config = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}

'''创建logger记录器'''
logger = logging.getLogger('my_logger')

# 输出到控制台
console_handler = logging.StreamHandler()

'''日志级别设置'''
log_level = os.getenv('LOG_LEVEL', 'INFO')
if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    level = getattr(logging, log_level)
else:
    level = getattr(logging, 'INFO')

logger.setLevel(level)
console_handler.setLevel(level)

# 输出到文件
log_export = os.getenv('LOG_EXPORT', 'False')
if log_export.lower() == 'true':
    path = os.getenv('LOG_PATH', '/var/tmp/emby_notifier_tg/')
    os.makedirs(path, exist_ok=True)
    fileName = datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
    file_handler = logging.FileHandler(filename=os.path.join(path, fileName), mode='a', encoding='utf8')
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(filename)s|%(funcName)s|%(lineno)d] [%(levelname)s] : %(message)s',
        datefmt='%Y-%m-%d  %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)


class DBHandler(logging.Handler):
    """将日志写入 SQLite 数据库"""
    def __init__(self, port_id=None):
        super().__init__()
        self.port_id = port_id

    def emit(self, record):
        try:
            import db
            module = getattr(record, 'port_id', self.port_id)
            db.add_log(record.levelname, record.getMessage(), record.name, module)
        except Exception:
            pass  # 避免日志写入失败影响主流程


'''控制台格式'''
console_formatter = colorlog.ColoredFormatter(
    fmt='%(log_color)s[%(levelname)s] %(message)s',
    log_colors=log_colors_config
)
console_handler.setFormatter(console_formatter)

'''添加处理器'''
logger.addHandler(console_handler)
if log_export.lower() == 'true':
    logger.addHandler(file_handler)


def setup_db_logging(port_id=None):
    """启用数据库日志"""
    for h in logger.handlers:
        if isinstance(h, DBHandler):
            return
    db_handler = DBHandler(port_id)
    db_handler.setLevel(logger.level)
    logger.addHandler(db_handler)


'''敏感数据脱敏'''
class SensitiveData:
    def __init__(self, data):
        self.data = data

    def __str__(self):
        if log_level == 'DEBUG':
            return str(self.data)
        return '*** Sensitive Data ***'
