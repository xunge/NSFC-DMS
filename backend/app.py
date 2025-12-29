"""主应用入口"""
from flask import Flask
import logging
import os
import sys

# 将当前目录添加到 Python 路径，支持直接运行
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from models import init_db
from routes import register_routes

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 注册路由
register_routes(app)

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动应用
    logger.info("启动Flask应用...")
    app.run(debug=True, host='0.0.0.0', port=5002)
