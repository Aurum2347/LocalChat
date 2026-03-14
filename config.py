import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'local-chat-secret-key-123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///localchat.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = 5000
    HOST = '0.0.0.0'
    
    # === НАСТРОЙКИ СЕССИЙ ===
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # Сессия живёт 30 минут
    SESSION_REFRESH_EACH_REQUEST = True  # Продлевать сессию при каждом запросе
    
    # Версия проекта
    VERSION = '2.0.0'
    VERSION_NAME = 'LocalChat'
    
    # Загрузка файлов
    UPLOAD_FOLDER = 'uploads'
    AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
    FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'files')
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_AVATAR_SIZE = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp3', 'mp4', 'webm', 'pdf', 'txt', 'doc', 'docx'}
    ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}