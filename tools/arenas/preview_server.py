"""场地预览用的小静态服务器（系统 python3，只用标准库）：以仓库根目录为根提供静态文件，
并接受 POST /save?path=art/review/arenas/<区域>/xxx.png 把页面里截的图写回审图目录（只允许写这个目录）。

    python3 tools/arenas/preview_server.py [端口，默认 4180]
    # 浏览器打开 http://127.0.0.1:4180/tools/arenas/preview.html?id=cathedral&shots=center,north,east
"""

import http.server
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = (ROOT / "art" / "review" / "arenas").resolve()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/save":
            self.send_error(404)
            return
        rel = parse_qs(url.query).get("path", [""])[0]
        dest = (ROOT / rel).resolve()
        if ALLOWED not in dest.parents or dest.suffix != ".png":
            self.send_error(403, "只允许写 art/review/arenas/**/*.png")
            return
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
        print("SAVED", dest, len(data), flush=True)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4180
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
