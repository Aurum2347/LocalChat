from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_from_directory
from models import User, Message, UploadedFile, MessageFile, db
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'files')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4', 'webm', 'pdf', 'txt', 'doc', 'docx', 'svg'}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_AVATAR_SIZE = 5 * 1024 * 1024

for folder in [UPLOAD_FOLDER, AVATAR_FOLDER, FILES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'image'
    elif ext in ['mp3', 'wav', 'ogg']:
        return 'audio'
    elif ext in ['mp4', 'webm', 'avi']:
        return 'video'
    else:
        return 'document'

# ==================== СТРАНИЦЫ ====================

@main_bp.route('/')
def index():
    return redirect(url_for('main.login'))

@main_bp.route('/login')
def login():
    return render_template('login.html')

@main_bp.route('/register')
def register():
    return render_template('register.html')

@main_bp.route('/chat')
def chat():
    return render_template('chat.html')

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

# ==================== API: АВТОРИЗАЦИЯ ====================

@main_bp.route('/api/register', methods=['POST'])
def register_api():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Нет данных'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400
    
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Имя: 3-20 символов'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Пользователь существует'}), 400
    
    new_user = User(username=username, password=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'id': new_user.id, 'username': new_user.username})

@main_bp.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Нет данных'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return jsonify({
            'success': True,
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname or user.username,
            'avatar': user.avatar,
            'about_me': user.about_me or ''
        })
    return jsonify({'error': 'Неверный логин или пароль'}), 401

@main_bp.route('/api/logout', methods=['POST'])
def logout_api():
    return jsonify({'success': True})

# ==================== API: ПОЛЬЗОВАТЕЛИ ====================

@main_bp.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'nickname': u.nickname or u.username,
        'avatar': u.avatar,
        'about_me': u.about_me or ''
    } for u in users])

# ==================== API: СООБЩЕНИЯ ====================

@main_bp.route('/api/messages', methods=['GET'])
def get_messages():
    msgs = Message.query.order_by(Message.timestamp.asc()).limit(100).all()
    result = []
    for m in msgs:
        msg_data = {
            'id': m.id,
            'text': m.text,
            'username': m.username,
            'user_id': m.user_id,
            'recipient_id': m.recipient_id if hasattr(m, 'recipient_id') else None,
            'timestamp': m.timestamp.strftime('%H:%M'),
            'files': [],
            'avatar': m.author.avatar if m.author else None,
            'nickname': m.author.nickname if m.author and hasattr(m.author, 'nickname') else m.username
        }
        for mf in m.files:
            f = mf.file
            msg_data['files'].append({
                'id': f.id,
                'filename': f.filename,
                'original_name': f.original_name,
                'file_type': f.file_type,
                'file_size': f.file_size
            })
        result.append(msg_data)
    return jsonify(result)

# ==================== API: ПРОФИЛЬ ====================

@main_bp.route('/api/profile/update', methods=['POST'])
def update_profile():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({'error': 'Нет ID'}), 400
    
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    new_nickname = request.form.get('nickname')
    new_about = request.form.get('about_me')
    
    if new_nickname is not None:
        user.nickname = new_nickname[:100]
    if new_about is not None:
        user.about_me = new_about[:500]
    
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename and allowed_file(file.filename):
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            if size <= MAX_AVATAR_SIZE:
                if user.avatar and user.avatar != 'default.png':
                    old = os.path.join(AVATAR_FOLDER, user.avatar)
                    if os.path.exists(old):
                        os.remove(old)
                ext = file.filename.rsplit('.', 1)[1].lower()
                fn = f"avatar_{user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
                file.save(os.path.join(AVATAR_FOLDER, fn))
                user.avatar = fn
    
    db.session.commit()
    return jsonify({
        'success': True,
        'username': user.username,
        'nickname': user.nickname or user.username,
        'about_me': user.about_me or '',
        'avatar': user.avatar
    })

# ==================== API: ФАЙЛЫ ====================

@main_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла в запросе'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Недопустимый формат'}), 400
    
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'Файл слишком большой'}), 400
    
    original_name = secure_filename(file.filename)
    filename = f"{int(datetime.utcnow().timestamp())}_{original_name}"
    filepath = os.path.join(FILES_FOLDER, filename)
    
    try:
        file.save(filepath)
    except Exception as e:
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500
    
    user_id = request.form.get('user_id')
    if not user_id:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'Нет ID пользователя'}), 400
    
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'Неверный формат ID пользователя'}), 400
    
    uploaded_file = UploadedFile(
        filename=filename,
        original_name=original_name,
        file_type=get_file_type(original_name),
        file_size=size,
        user_id=user_id_int
    )
    db.session.add(uploaded_file)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'file_id': uploaded_file.id,
        'filename': filename,
        'original_name': original_name,
        'file_type': uploaded_file.file_type,
        'file_size': size
    })

@main_bp.route('/api/file/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    f = UploadedFile.query.get(file_id)
    if not f:
        return jsonify({'error': 'Файл не найден'}), 404
    path = os.path.join(FILES_FOLDER, f.filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(f)
    db.session.commit()
    return jsonify({'success': True})

# ==================== СТАТИКА ====================

@main_bp.route('/uploads/files/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(FILES_FOLDER, filename)

@main_bp.route('/uploads/avatars/<path:filename>')
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)