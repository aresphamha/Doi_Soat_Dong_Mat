# -*- coding: utf-8 -*-
"""
SCM Local Tool Runner Service (Micro-Daemon)
Cung cấp REST API & Server-Sent Events (SSE) để Dashboard Web (trên GitHub Pages) 
có thể điều khiển và kích hoạt chạy trực tiếp toàn bộ Tool Spam & Đối Soát SCM trên máy tính cục bộ.
"""

import os
import sys
import json
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Safe stdout/stderr initialization for pythonw (headless background daemon)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8088
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SPAM_RUNNER_SCRIPT = os.path.join(ROOT_DIR, "SPAM_PHIEU_CHUYEN", "run_spam_tool.py")
PYTHON_EXE = sys.executable

# Lưu lịch sử log chạy gần nhất
LATEST_EXECUTION = {
    "tool": None,
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "logs": [],
    "returncode": 0
}
EXECUTION_LOCK = threading.Lock()

def get_stores_list():
    try:
        from SPAM_PHIEU_CHUYEN.run_spam_tool import find_mapping_file
        excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
        if not os.path.exists(excel_path):
            excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        import pandas as pd
        df = pd.read_excel(excel_path, dtype=str)
        stores = []
        for _, row in df.iterrows():
            st_id = str(row.get('ID ST', '')).strip()
            name = str(row.get('Tên Siêu thị', '')).strip()
            short = str(row.get('Tên viết tắt', '')).strip()
            chat_id = str(row.get('CHAT ID', '')).strip()
            if st_id and st_id != 'nan':
                stores.append({
                    "id": st_id,
                    "name": name,
                    "short": short if short != 'nan' else st_id,
                    "chat_id": chat_id if chat_id != 'nan' else ""
                })
        return stores
    except Exception as e:
        print(f"⚠️ Lỗi đọc danh sách Siêu thị: {e}")
        return []

def get_all_chat_ids():
    json_path = os.path.join(ROOT_DIR, "CONFIG_DATA_STORES.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    stores = get_stores_list()
    for s in stores:
        s['chat_id_dm'] = s.get('chat_id', '')
        s['chat_id_rc'] = ''
    return stores

def update_store_chat_ids(store_id, chat_id_dm=None, chat_id_rc=None, store_name=None):
    if not store_id:
        return False, "Thiếu Mã Siêu Thị (store_id)!"
    
    store_id = str(store_id).strip().upper()
    
    # 1. Update Dong Mat Excel files
    dm_files = [
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'Danh_Sach_Sieu_Thi_Dong_Mat.xlsx'),
        os.path.join(ROOT_DIR, 'TOOLS_DOI_SOAT', 'DONG_MAT', 'Danh sách Siêu thị.xlsx'),
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'HẬU KIỂM THỊ CÁ', 'Danh sách Siêu thị.xlsx'),
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'CHI TIẾT MÁT', 'Danh sách Siêu thị.xlsx'),
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'CHI TIẾT THỊT CÁ', 'Danh sách Siêu thị.xlsx')
    ]
    
    import pandas as pd
    if chat_id_dm is not None or store_name is not None:
        for f in dm_files:
            if os.path.exists(f):
                try:
                    df = pd.read_excel(f, dtype=str)
                    mask = (df['ID ST'].astype(str).str.strip().str.upper() == store_id)
                    if mask.any():
                        if chat_id_dm is not None:
                            df.loc[mask, 'CHAT ID'] = str(chat_id_dm).strip()
                        if store_name is not None and 'Tên Siêu thị' in df.columns:
                            df.loc[mask, 'Tên Siêu thị'] = str(store_name).strip()
                    else:
                        new_row = {'ID ST': store_id, 'Tên Siêu thị': store_name or store_id, 'Tên viết tắt': store_id, 'CHAT ID': str(chat_id_dm or '')}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(f, index=False)
                except Exception as e:
                    print(f"Error updating {f}: {e}")

    # 2. Update Rau Cu Excel files
    rc_files = [
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'Danh_Sach_Sieu_Thi_Rau_Cu.xlsx'),
        os.path.join(ROOT_DIR, 'TOOLS_DOI_SOAT', 'RAU_CU', 'Danh sách Siêu thị.xlsx'),
        os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'HẬU KIỂM RAU', 'Danh sách Siêu thị.xlsx')
    ]
    
    if chat_id_rc is not None or store_name is not None:
        for f in rc_files:
            if os.path.exists(f):
                try:
                    df = pd.read_excel(f, dtype=str)
                    id_col = 'ID ST TƯƠNG ỨNG' if 'ID ST TƯƠNG ỨNG' in df.columns else 'ID ST'
                    mask = (df[id_col].astype(str).str.strip().str.upper() == store_id)
                    if mask.any():
                        if chat_id_rc is not None:
                            df.loc[mask, 'CHAT ID'] = str(chat_id_rc).strip()
                        if store_name is not None and 'Tên Siêu thị' in df.columns:
                            df.loc[mask, 'Tên Siêu thị'] = str(store_name).strip()
                    else:
                        new_row = {'THÔNG TIN KHO': 'KRC', id_col: store_id, 'CHAT ID': str(chat_id_rc or ''), 'Tên Siêu thị': store_name or store_id}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(f, index=False)
                except Exception as e:
                    print(f"Error updating {f}: {e}")

    # 3. Update CONFIG_DATA_STORES.json
    json_path = os.path.join(ROOT_DIR, 'CONFIG_DATA_STORES.json')
    try:
        data = []
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
        found = False
        for item in data:
            if item.get('id', '').strip().upper() == store_id:
                if chat_id_dm is not None: item['chat_id_dm'] = str(chat_id_dm).strip()
                if chat_id_rc is not None: item['chat_id_rc'] = str(chat_id_rc).strip()
                if store_name is not None: item['name'] = str(store_name).strip()
                found = True
                break
        if not found:
            data.append({
                'id': store_id,
                'name': store_name or store_id,
                'short': store_id,
                'chat_id_dm': str(chat_id_dm or ''),
                'chat_id_rc': str(chat_id_rc or '')
            })
        data = sorted(data, key=lambda x: x.get('id', ''))
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(data, jf, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error updating JSON: {e}")

    return True, f"✅ Đã cập nhật Chat ID cho Siêu thị {store_id} thành công vào toàn bộ file Excel!"

import ctypes

kernel32 = ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll

CURRENT_RUNNING_PROC = None
IS_CURRENT_PAUSED = False

def suspend_process(proc):
    global IS_CURRENT_PAUSED
    if proc and proc.poll() is None:
        try:
            h = kernel32.OpenProcess(0x0800 | 0x0001, False, proc.pid)
            if h:
                ntdll.NtSuspendProcess(h)
                kernel32.CloseHandle(h)
                IS_CURRENT_PAUSED = True
                return True
        except Exception as e:
            print(f"Error suspending process: {e}")
    return False

def resume_process(proc):
    global IS_CURRENT_PAUSED
    if proc and proc.poll() is None:
        try:
            h = kernel32.OpenProcess(0x0800 | 0x0001, False, proc.pid)
            if h:
                ntdll.NtResumeProcess(h)
                kernel32.CloseHandle(h)
                IS_CURRENT_PAUSED = False
                return True
        except Exception as e:
            print(f"Error resuming process: {e}")
    return False

def terminate_process(proc):
    global CURRENT_RUNNING_PROC, IS_CURRENT_PAUSED
    if proc and proc.poll() is None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            proc.terminate()
        except Exception as e:
            print(f"Error terminating process: {e}")
    CURRENT_RUNNING_PROC = None
    IS_CURRENT_PAUSED = False

class SCMRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health" or path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "status": "online",
                "service": "SCM Local Runner Service",
                "version": "2.2",
                "port": PORT,
                "current_status": "paused" if IS_CURRENT_PAUSED else (LATEST_EXECUTION["status"] if CURRENT_RUNNING_PROC else "idle"),
                "is_running": CURRENT_RUNNING_PROC is not None and CURRENT_RUNNING_PROC.poll() is None,
                "is_paused": IS_CURRENT_PAUSED,
                "last_tool": LATEST_EXECUTION["tool"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/api/stores" or path == "/stores":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            stores = get_stores_list()
            resp = {
                "success": True,
                "total": len(stores),
                "stores": stores
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/api/chat_ids" or path == "/api/stores_all":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            stores = get_all_chat_ids()
            resp = {
                "success": True,
                "total": len(stores),
                "stores": stores
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = dict(LATEST_EXECUTION)
            resp["is_running"] = CURRENT_RUNNING_PROC is not None and CURRENT_RUNNING_PROC.poll() is None
            resp["is_paused"] = IS_CURRENT_PAUSED
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/pause" or path == "/api/pause":
            ok = suspend_process(CURRENT_RUNNING_PROC)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": ok,
                "status": "paused" if ok else "not_running",
                "message": "⏸️ Đã tạm dừng công cụ thành công!" if ok else "⚠️ Không có tiến trình nào đang chạy để tạm dừng."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/resume" or path == "/api/resume":
            ok = resume_process(CURRENT_RUNNING_PROC)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": ok,
                "status": "running" if ok else "not_running",
                "message": "▶️ Đã tiếp tục chạy công cụ!" if ok else "⚠️ Không có tiến trình nào đang tạm dừng để tiếp tục."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/cancel" or path == "/api/cancel" or path == "/stop":
            terminate_process(CURRENT_RUNNING_PROC)
            LATEST_EXECUTION["status"] = "cancelled"
            LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": True,
                "status": "cancelled",
                "message": "🛑 Đã hủy và dừng chạy công cụ ngay lập tức!"
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/run":
            tool = params.get('tool', ['all'])[0]
            target_date = params.get('date', [''])[0]
            dry_run = params.get('dry_run', ['false'])[0].lower() in ['true', '1', 'yes']
            stores = params.get('stores', ['ALL'])[0]
            message = params.get('message', [''])[0]
            tag_roles = params.get('tag_roles', ['true'])[0].lower() in ['true', '1', 'yes']
            
            result = run_tool_sync(tool, target_date, dry_run, stores, message, tag_roles)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/stream" or path == "/stream_custom":
            # Server-Sent Events (SSE) để stream logs trực tiếp về Web UI
            tool = params.get('tool', ['all'])[0]
            target_date = params.get('date', [''])[0]
            dry_run = params.get('dry_run', ['false'])[0].lower() in ['true', '1', 'yes']
            stores = params.get('stores', ['ALL'])[0]
            message = params.get('message', [''])[0]
            tag_roles = params.get('tag_roles', ['true'])[0].lower() in ['true', '1', 'yes']

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self._send_cors_headers()
            self.end_headers()

            self._stream_tool_execution(tool, target_date, dry_run, stores, message, tag_roles)
            return

        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            data = {}

        if path == "/pause" or path == "/api/pause":
            ok = suspend_process(CURRENT_RUNNING_PROC)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": ok,
                "status": "paused" if ok else "not_running",
                "message": "⏸️ Đã tạm dừng công cụ thành công!" if ok else "⚠️ Không có tiến trình nào đang chạy để tạm dừng."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/resume" or path == "/api/resume":
            ok = resume_process(CURRENT_RUNNING_PROC)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": ok,
                "status": "running" if ok else "not_running",
                "message": "▶️ Đã tiếp tục chạy công cụ!" if ok else "⚠️ Không có tiến trình nào đang tạm dừng để tiếp tục."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/cancel" or path == "/api/cancel" or path == "/stop":
            terminate_process(CURRENT_RUNNING_PROC)
            LATEST_EXECUTION["status"] = "cancelled"
            LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": True,
                "status": "cancelled",
                "message": "🛑 Đã hủy và dừng chạy công cụ ngay lập tức!"
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/api/chat_id/update" or path == "/api/chat_ids/update":
            store_id = data.get('store_id', data.get('id', '')).strip()
            chat_id_dm = data.get('chat_id_dm', data.get('chat_id', None))
            chat_id_rc = data.get('chat_id_rc', None)
            store_name = data.get('store_name', data.get('name', None))
            
            ok, msg = update_store_chat_ids(store_id, chat_id_dm, chat_id_rc, store_name)
            self.send_response(200 if ok else 400)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": ok,
                "message": msg,
                "stores": get_all_chat_ids() if ok else []
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/run" or path == "/api/spam_custom":
            tool = data.get('tool', 'spam_tu_chon' if path == '/api/spam_custom' else 'all')
            target_date = data.get('date', '')
            dry_run = data.get('dry_run', False)
            stores = data.get('stores', 'ALL')
            message = data.get('message', '')
            tag_roles = data.get('tag_roles', True)
            
            result = run_tool_sync(tool, target_date, dry_run, stores, message, tag_roles)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def _stream_tool_execution(self, tool, target_date, dry_run, stores="ALL", message="", tag_roles=True):
        global CURRENT_RUNNING_PROC, IS_CURRENT_PAUSED
        cmd = [PYTHON_EXE, SPAM_RUNNER_SCRIPT, "--tool", tool]
        if target_date:
            cmd.extend(["--date", target_date])
        if dry_run:
            cmd.append("--dry-run")
        if tool == "spam_tu_chon":
            if not message or not str(message).strip():
                err_event = {"type": "error", "msg": "❌ LỖI BẢO VỆ: Bạn chưa nhập nội dung tin nhắn cần gửi! Đã chặn thực thi để không gửi mẫu thông báo nhầm."}
                self.wfile.write(f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
                return
            if stores:
                cmd.extend(["--stores", stores])
            if message:
                cmd.extend(["--message", message])
            if not tag_roles:
                cmd.append("--no-tags")

        try:
            date_label = target_date if target_date else "Mặc định"
            tool_title = f"Spam Tùy Chọn ({stores})" if tool == "spam_tu_chon" else tool
            start_payload = {'type': 'start', 'msg': f"🚀 Bắt đầu thực thi: {tool_title} (Date: {date_label})"}
            self.wfile.write(f"data: {json.dumps(start_payload, ensure_ascii=False)}\n\n".encode('utf-8'))
            self.wfile.flush()

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=ROOT_DIR,
                bufsize=1
            )
            CURRENT_RUNNING_PROC = proc
            IS_CURRENT_PAUSED = False

            for line in proc.stdout:
                clean_line = line.rstrip()
                if clean_line:
                    event = {"type": "log", "line": clean_line}
                    self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode('utf-8'))
                    self.wfile.flush()

            proc.wait()
            ret = proc.returncode
            end_event = {
                "type": "end",
                "returncode": ret,
                "msg": "✅ Thực thi hoàn tất thành công!" if ret == 0 else f"⚠️ Thực thi kết thúc (Mã: {ret})"
            }
            self.wfile.write(f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n".encode('utf-8'))
            self.wfile.flush()

        except Exception as e:
            err_event = {"type": "error", "msg": f"❌ Lỗi thực thi: {str(e)}"}
            try:
                self.wfile.write(f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
            except Exception:
                pass
        finally:
            CURRENT_RUNNING_PROC = None
            IS_CURRENT_PAUSED = False


def run_tool_sync(tool, target_date, dry_run, stores="ALL", message="", tag_roles=True):
    global LATEST_EXECUTION, CURRENT_RUNNING_PROC, IS_CURRENT_PAUSED
    with EXECUTION_LOCK:
        LATEST_EXECUTION["tool"] = tool
        LATEST_EXECUTION["status"] = "running"
        LATEST_EXECUTION["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        LATEST_EXECUTION["logs"] = []
        LATEST_EXECUTION["returncode"] = None

        cmd = [PYTHON_EXE, SPAM_RUNNER_SCRIPT, "--tool", tool]
        if target_date:
            cmd.extend(["--date", target_date])
        if dry_run:
            cmd.append("--dry-run")
        if tool == "spam_tu_chon":
            if not message or not str(message).strip():
                LATEST_EXECUTION["status"] = "error"
                LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                err_msg = "❌ LỖI BẢO VỆ: Bạn chưa nhập nội dung tin nhắn! Đã chặn thực thi để không gửi mẫu thông báo nhầm."
                LATEST_EXECUTION["logs"] = [err_msg]
                LATEST_EXECUTION["returncode"] = -1
                return {
                    "success": False,
                    "tool": tool,
                    "returncode": -1,
                    "error": err_msg,
                    "logs": err_msg
                }
            if stores:
                cmd.extend(["--stores", stores])
            if message:
                cmd.extend(["--message", message])
            if not tag_roles:
                cmd.append("--no-tags")

        try:
            print(f"👉 [LOCAL RUNNER] Chạy lệnh: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=ROOT_DIR
            )
            CURRENT_RUNNING_PROC = proc
            IS_CURRENT_PAUSED = False
            logs = []
            for line in proc.stdout:
                line_str = line.rstrip()
                logs.append(line_str)
                print(line_str)

            proc.wait()
            LATEST_EXECUTION["status"] = "success" if proc.returncode == 0 else "error"
            LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            LATEST_EXECUTION["logs"] = logs
            LATEST_EXECUTION["returncode"] = proc.returncode

            return {
                "success": proc.returncode == 0,
                "tool": tool,
                "returncode": proc.returncode,
                "logs": "\n".join(logs),
                "started_at": LATEST_EXECUTION["started_at"],
                "completed_at": LATEST_EXECUTION["completed_at"]
            }
        except Exception as e:
            LATEST_EXECUTION["status"] = "error"
            LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            LATEST_EXECUTION["logs"].append(f"Lỗi: {e}")
            LATEST_EXECUTION["returncode"] = -1
            return {
                "success": False,
                "tool": tool,
                "returncode": -1,
                "error": str(e),
                "logs": f"❌ Lỗi khởi chạy: {e}"
            }
        finally:
            CURRENT_RUNNING_PROC = None
            IS_CURRENT_PAUSED = False


def start_server():
    log_path = os.path.join(ROOT_DIR, "local_runner_service.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting SCM Local Runner on port {PORT}...\n")
        server = ThreadingHTTPServer(('0.0.0.0', PORT), SCMRequestHandler)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server started successfully.\n")
        print("=" * 70)
        print(f"🚀 SCM LOCAL RUNNER SERVICE ĐANG CHẠY TẠI: http://localhost:{PORT}")
        print(f"📡 Cho phép Web Dashboard trên GitHub Pages điều khiển trực tiếp máy tính.")
        print("=" * 70)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng server...")
        server.server_close()
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] FATAL ERROR: {e}\n")
        print(f"❌ FATAL ERROR: {e}")

if __name__ == "__main__":
    start_server()
