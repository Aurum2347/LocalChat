from flask import request
from flask_socketio import emit, join_room, leave_room
from models import User, Message, UploadedFile, MessageFile, db
from datetime import datetime

def init_socket_events(socketio, connected_clients):
    
    @socketio.on('connect')
    def connect():
        print(f"✓ Клиент подключился: {request.sid}")
    
    @socketio.on('disconnect')
    def disconnect():
        # Удаляем из списка при отключении
        if request.sid in connected_clients:
            user_info = connected_clients.pop(request.sid)
            print(f"✗ Клиент отключился: {user_info.get('nickname', user_info.get('username', 'Unknown'))} ({request.sid})")
        else:
            print(f"✗ Клиент отключился: {request.sid}")
    
    @socketio.on('register_client')
    def register_client(data):
        """Регистрация клиента с информацией о пользователе"""
        try:
            user_id = data.get('user_id')
            username = data.get('username')
            nickname = data.get('nickname', username)
            
            if user_id and username:
                connected_clients[request.sid] = {
                    'user_id': user_id,
                    'username': username,
                    'nickname': nickname,
                    'sid': request.sid
                }
                print(f"👤 Зарегистрирован: {nickname} (@{username}) [ID: {user_id}]")
        except Exception as e:
            print(f"❌ Ошибка регистрации клиента: {e}")
    
    @socketio.on('send_message')
    def handle_message(data):
        try:
            if not data or not isinstance(data, dict):
                return
            
            user_id = data.get('user_id')
            username = data.get('username')
            text = data.get('text', '').strip()
            file_ids = data.get('files', [])
            recipient_id = data.get('recipient_id')
            
            if not user_id or not username:
                return
            
            if not text and not file_ids:
                return

            if len(text) > 500:
                text = text[:500]

            user = User.query.get(user_id)
            if not user or user.username != username:
                return

            new_msg = Message(
                text=text,
                username=username,
                user_id=user_id,
                recipient_id=int(recipient_id) if recipient_id else None,
                timestamp=datetime.utcnow()
            )
            db.session.add(new_msg)
            db.session.flush()

            if file_ids:
                for fid in file_ids:
                    file = UploadedFile.query.get(fid)
                    if file:
                        msg_file = MessageFile(file_id=file.id, message_id=new_msg.id)
                        db.session.add(msg_file)
            
            db.session.commit()

            msg_data = {
                'id': new_msg.id,
                'text': new_msg.text,
                'username': new_msg.username,
                'user_id': new_msg.user_id,
                'recipient_id': new_msg.recipient_id,
                'timestamp': new_msg.timestamp.strftime('%H:%M'),
                'files': [],
                'avatar': user.avatar,
                'nickname': getattr(user, 'nickname', user.username)
            }

            for mf in new_msg.files:
                f = mf.file
                msg_data['files'].append({
                    'id': f.id,
                    'filename': f.filename,
                    'original_name': f.original_name,
                    'file_type': f.file_type,
                    'file_size': f.file_size
                })

            if recipient_id:
                emit('new_message', msg_data, room=f'dm_{recipient_id}')
                emit('new_message', msg_data, room=f'dm_{user_id}')
            else:
                emit('new_message', msg_data, broadcast=True)
            
            # Показываем никнейм в логах
            nickname = getattr(user, 'nickname', username)
            print(f"💬 Сообщение от {nickname} (@{username}): {text[:50]}...")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Ошибка: {e}")

    @socketio.on('typing')
    def handle_typing(data):
        try:
            username = data.get('username')
            if username:
                emit('user_typing', {'username': username}, broadcast=True, include_self=False)
        except:
            pass

    @socketio.on('join_room')
    def handle_join(data):
        try:
            room = data.get('room', 'global')
            join_room(room)
        except:
            pass

    @socketio.on('leave_room')
    def handle_leave(data):
        try:
            room = data.get('room', 'global')
            leave_room(room)
        except:
            pass

    @socketio.on('delete_message')
    def handle_delete_message(data):
        try:
            msg_id = data.get('id')
            user_id = data.get('user_id')
            
            if not msg_id or not user_id:
                return
            
            msg = Message.query.get(msg_id)
            if not msg or msg.user_id != user_id:
                return
            
            for mf in msg.files:
                file = UploadedFile.query.get(mf.file_id)
                if file:
                    db.session.delete(file)
            
            db.session.delete(msg)
            db.session.commit()
            
            emit('message_deleted', {'id': msg_id}, broadcast=True)
            print(f"🗑 Сообщение {msg_id} удалено")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Ошибка удаления: {e}")