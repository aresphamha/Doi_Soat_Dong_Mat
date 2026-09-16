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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# UTF-8 Encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8088
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SPAM_RUNNER_SCRIPT = os.path.join(ROOT_DIR, "SPAM_PHIEU_CHUYEN", "run_spam_tool.py")
PYTHON_EXE = sys.executable

# Lưu lịch sử log chạy gần nhất và tiến trình đang thực thi
LATEST_EXECUTION = {
    "tool": None,
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "logs": [],
    "returncode": 0
}
EXECUTION_LOCK = threading.Lock()
ACTIVE_PROCESS = None

def stop_active_process():
    global ACTIVE_PROCESS, LATEST_EXECUTION
    with EXECUTION_LOCK:
        if ACTIVE_PROCESS is not None:
            try:
                print("🛑 [STOP REQUEST] Nhận được yêu cầu dừng tiến trình đang chạy...")
                ACTIVE_PROCESS.terminate()
                time.sleep(0.2)
                if ACTIVE_PROCESS.poll() is None:
                    ACTIVE_PROCESS.kill()
                LATEST_EXECUTION["status"] = "stopped"
                LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                LATEST_EXECUTION["logs"].append("🛑 [ĐÃ DỪNG] Người dùng đã bấm dừng công cụ thành công.")
                ACTIVE_PROCESS = None
                return True
            except Exception as e:
                print(f"⚠️ Lỗi khi dừng tiến trình: {e}")
                return False
        return False

class SCMRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

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
                "version": "2.1",
                "port": PORT,
                "current_status": LATEST_EXECUTION["status"],
                "last_tool": LATEST_EXECUTION["tool"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_EXECUTION, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/stop" or path == "/cancel":
            stopped = stop_active_process()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": True,
                "stopped": stopped,
                "msg": "✅ Đã dừng tiến trình thành công!" if stopped else "ℹ️ Không có tiến trình nào đang chạy để dừng."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/run":
            tool = params.get('tool', ['all'])[0]
            target_date = params.get('date', [''])[0]
            dry_run = params.get('dry_run', ['false'])[0].lower() in ['true', '1', 'yes']
            
            result = run_tool_sync(tool, target_date, dry_run)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/stream":
            tool = params.get('tool', ['all'])[0]
            target_date = params.get('date', [''])[0]
            dry_run = params.get('dry_run', ['false'])[0].lower() in ['true', '1', 'yes']

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self._send_cors_headers()
            self.end_headers()

            self._stream_tool_execution(tool, target_date, dry_run)
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

        if path == "/stop" or path == "/cancel":
            stopped = stop_active_process()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "success": True,
                "stopped": stopped,
                "msg": "✅ Đã dừng tiến trình thành công!" if stopped else "ℹ️ Không có tiến trình nào đang chạy để dừng."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        elif path == "/run":
            tool = data.get('tool', 'all')
            target_date = data.get('date', '')
            dry_run = data.get('dry_run', False)
            
            result = run_tool_sync(tool, target_date, dry_run)
            
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

    def _stream_tool_execution(self, tool, target_date, dry_run):
        global ACTIVE_PROCESS, LATEST_EXECUTION
        cmd = [PYTHON_EXE, SPAM_RUNNER_SCRIPT, "--tool", tool]
        if target_date:
            cmd.extend(["--date", target_date])
        if dry_run:
            cmd.append("--dry-run")

        try:
            date_label = target_date if target_date else "Mặc định"
            start_payload = {'type': 'start', 'msg': f"🚀 Bắt đầu thực thi: {tool} (Date: {date_label})"}
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
            with EXECUTION_LOCK:
                ACTIVE_PROCESS = proc
                LATEST_EXECUTION["tool"] = tool
                LATEST_EXECUTION["status"] = "running"
                LATEST_EXECUTION["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            for line in proc.stdout:
                clean_line = line.rstrip()
                if clean_line:
                    event = {"type": "log", "line": clean_line}
                    try:
                        self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode('utf-8'))
                        self.wfile.flush()
                    except Exception:
                        break

            proc.wait()
            ret = proc.returncode
            with EXECUTION_LOCK:
                ACTIVE_PROCESS = None
                LATEST_EXECUTION["status"] = "success" if ret == 0 else ("stopped" if ret == 15 or ret == -15 or ret == 1 else "error")
                LATEST_EXECUTION["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            end_event = {
                "type": "end",
                "returncode": ret,
                "msg": "✅ Thực thi hoàn tất thành công!" if ret == 0 else f"⚠️ Thực thi đã dừng / kết thúc (Mã: {ret})"
            }
            try:
                self.wfile.write(f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
            except Exception:
                pass

        except Exception as e:
            with EXECUTION_LOCK:
                ACTIVE_PROCESS = None
            err_event = {"type": "error", "msg": f"❌ Lỗi thực thi: {str(e)}"}
            try:
                self.wfile.write(f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
            except Exception:
                pass


def run_tool_sync(tool, target_date, dry_run):
    global LATEST_EXECUTION
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


def start_server():
    server = HTTPServer(('0.0.0.0', PORT), SCMRequestHandler)
    print("=" * 70)
    print(f"🚀 SCM LOCAL RUNNER SERVICE ĐANG CHẠY TẠI: http://localhost:{PORT}")
    print(f"📡 Cho phép Web Dashboard trên GitHub Pages điều khiển trực tiếp máy tính.")
    print("=" * 70)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng server...")
        server.server_close()

if __name__ == "__main__":
    start_server()
