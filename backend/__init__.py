"""后端包初始化"""
from .app import app
from .models import init_db

__all__ = ['app', 'init_db']
