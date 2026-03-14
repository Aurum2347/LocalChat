import logging
import socket
import signal
import sys
from flask import Flask
from flask_socketio import SocketIO
from config import Config
from database import init_db
from routes import main_bp
from socket_handler import init_socket_events

# Отключаем дублирование логов Werkzeug
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Глобальное хранилище подключенных клиентов
connected_clients = {}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    init_db(app)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)
    init_socket_events(socketio, connected_clients)
    app.register_blueprint(main_bp)
    return app, socketio

def signal_handler(sig, frame):
    print('\n\n⚠ Завершение работы сервера...')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    app, socketio = create_app()
    local_ip = get_local_ip()
    
    # Печатаем только один раз (убираем дублирование Flask)
    print("\n" + "=" * 80)
    print("  🚀 LocalChat запущен!")
    print(f"  📍 Локальный адрес: http://{local_ip}:{Config.PORT}")
    print(f"  📍 Также доступен: http://127.0.0.1:{Config.PORT}")
    print("=" * 80)
    print("  Нажми Ctrl+C для остановки сервера\n")
    
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=False, allow_unsafe_werkzeug=True)