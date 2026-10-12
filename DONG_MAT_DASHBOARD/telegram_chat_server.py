from sync_telegram_groups import is_broadcast_or_spam_message, analyze_message_priority
# -*- coding: utf-8 -*-
"""
Telegram SCM Chat Server - Realtime 2-Way Chat Engine
Sử dụng aiohttp + Telethon kết nối tài khoản chính: 0978009295 (KFM - SCM - Hà Phạm - SC007251)
Cung cấp API đọc tin nhắn và gửi phản hồi trực tiếp vào bất kỳ nhóm Telegram nào.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from aiohttp import web

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

API_ID = 28938971
API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(CURRENT_DIR, 'user_session.session')
if not os.path.exists(SESSION_PATH):
    alt_paths = [
        r"g:\My Drive\Đối soát SCM\DONG_MAT_DASHBOARD\user_session.session",
        r"C:\Users\Thu Ha\Doi_Soat_Dong_Mat\DONG_MAT_DASHBOARD\user_session.session"
    ]
    for p in alt_paths:
        if os.path.exists(p):
            SESSION_PATH = p
            break

session_base = SESSION_PATH.replace('.session', '')
client = TelegramClient(session_base, API_ID, API_HASH)

# CORS middleware
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except Exception as e:
            response = web.json_response({"error": str(e)}, status=500)
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

async def handle_status(request):
    try:
        is_auth = await client.is_user_authorized()
        if not is_auth:
            return web.json_response({"connected": False, "error": "Chưa xác thực session"})
        me = await client.get_me()
        return web.json_response({
            "connected": True,
            "user_id": me.id,
            "name": f"{me.first_name} {me.last_name or ''}".strip(),
            "phone": me.phone or "0978009295",
            "username": me.username or ""
        })
    except Exception as e:
        return web.json_response({"connected": False, "error": str(e)})

async def handle_get_messages(request):
    chat_id_str = request.query.get('chat_id', '').strip()
    limit = int(request.query.get('limit', 30))
    if not chat_id_str:
        return web.json_response({"error": "Thiếu tham số chat_id"}, status=400)
    
    try:
        chat_id = int(chat_id_str)
        entity = await client.get_entity(chat_id)
        me = await client.get_me()
        my_id = me.id if me else None

        messages_data = []
        raw_msgs = await client.get_messages(entity, limit=limit)
        
        # Sort chronologically (oldest to newest)
        raw_msgs = list(reversed(raw_msgs))

        for m in raw_msgs:
            sender = await m.get_sender()
            sender_id = getattr(sender, 'id', None)
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', '') or 'Thành viên'
            if getattr(sender, 'last_name', ''):
                sender_name += f" {sender.last_name}"
            
            is_me = (sender_id == my_id)

            media_info = None
            if m.media:
                media_type = type(m.media).__name__
                if 'Photo' in media_type:
                    media_info = "📷 Hình ảnh / Chứng từ"
                elif 'Document' in media_type:
                    media_info = "📄 Tài liệu đính kèm"
                else:
                    media_info = f"📎 Đính kèm ({media_type})"

            time_str = m.date.strftime('%H:%M • %d/%m/%Y') if m.date else ''
            time_short = m.date.strftime('%H:%M') if m.date else ''
            m_text = m.text or ""
            is_spam = is_broadcast_or_spam_message(m_text)
            p_level, p_badge, p_reason = analyze_message_priority(m_text, not is_me, bool(media_info), is_spam)

            messages_data.append({
                "id": m.id,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "is_me": is_me,
                "text": m_text,
                "media_info": media_info,
                "time": time_str,
                "time_short": time_short,
                "is_spam": is_spam,
                "priority_level": p_level,
                "priority_badge": p_badge,
                "priority_reason": p_reason
            })

        group_title = getattr(entity, 'title', str(chat_id))

        return web.json_response({
            "success": True,
            "chat_id": chat_id_str,
            "group_title": group_title,
            "count": len(messages_data),
            "messages": messages_data
        })
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def handle_send_message(request):
    try:
        data = await request.json()
        chat_id_str = str(data.get('chat_id', '')).strip()
        text = str(data.get('text', '')).strip()

        if not chat_id_str or not text:
            return web.json_response({"error": "Thiếu chat_id hoặc nội dung tin nhắn"}, status=400)

        chat_id = int(chat_id_str)
        entity = await client.get_entity(chat_id)
        sent_msg = await client.send_message(entity, text)
        me = await client.get_me()

        return web.json_response({
            "success": True,
            "message_id": sent_msg.id,
            "chat_id": chat_id_str,
            "text": text,
            "time": sent_msg.date.strftime('%H:%M • %d/%m/%Y'),
            "time_short": sent_msg.date.strftime('%H:%M'),
            "sender_name": f"{me.first_name} {me.last_name or ''}".strip(),
            "is_me": True
        })
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def init_app():
    await client.connect()
    if not await client.is_user_authorized():
        print("CẢNH BÁO: Session Telethon chưa được xác thực!")
    else:
        me = await client.get_me()
        print(f"✅ Đã kết nối Telegram thành công: {me.first_name} ({me.phone})")

    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get('/api/status', handle_status)
    app.router.add_get('/api/messages', handle_get_messages)
    app.router.add_post('/api/send', handle_send_message)

    # Serve static root index
    root_dir = os.path.dirname(CURRENT_DIR)
    target_static = None
    for candidate in [root_dir, r'C:\Users\Thu Ha\Doi_Soat_Dong_Mat', r'g:\My Drive\Đối soát SCM']:
        if os.path.exists(os.path.join(candidate, 'index.html')):
            target_static = candidate
            break

    if target_static:
        app.router.add_static('/', path=target_static, show_index=True)

    return app

if __name__ == '__main__':
    port = 8080
    print(f"================================================================")
    print(f"🚀 TELEGRAM SCM CHAT SERVER ĐANG KHỞI ĐỘNG...")
    print(f"📡 API & Web: http://localhost:{port}/")
    print(f"📱 Tài khoản: 0978009295 (KFM - SCM - Hà Phạm - SC007251)")
    print(f"================================================================")
    
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=port)
