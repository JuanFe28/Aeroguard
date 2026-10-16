import http.server
import socketserver
import os
import sys
import re
import time
import urllib.parse
import io

PORT = 3000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

def rewrite_html(data):
    try:
        text = data.decode("utf-8")
        ts = int(time.time())
        # Replace script src in index.html to force fresh entrypoint load
        text = re.sub(r'(src=["\']\./src/main\.js)(?:\?[^"\']*)?(["\'])', f'\\1?v={ts}\\2', text)
        return text.encode("utf-8")
    except Exception:
        return data

def rewrite_js(path, data):
    try:
        text = data.decode("utf-8")
        dir_path = os.path.dirname(path)
        def repl(m):
            prefix = m.group(1)
            rel_file = m.group(2)
            suffix = m.group(3)
            clean_rel = rel_file.split("?")[0]
            target = os.path.normpath(os.path.join(dir_path, clean_rel))
            v = int(os.path.getmtime(target)) if os.path.exists(target) else int(time.time())
            return f"{prefix}'{clean_rel}?v={v}'{suffix}"
        
        pattern = r"(from\s+|import\s*\(\s*)['\"](\.[^'\"]+\.js)(?:\?[^'\"]*)?['\"](\s*\)|\s*)"
        text = re.sub(pattern, repl, text)
        return text.encode("utf-8")
    except Exception:
        return data

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Ignore conditional request headers to prevent 304 Not Modified
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        if "If-None-Match" in self.headers:
            del self.headers["If-None-Match"]
        return super().do_GET()

    def send_head(self):
        clean_path = self.path.split("?")[0]
        path = self.translate_path(clean_path)

        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                self.send_response(http.HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break

        if not os.path.exists(path) or os.path.isdir(path):
            return super().send_head()

        try:
            with open(path, "rb") as f:
                content = f.read()
        except OSError:
            self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")
            return None

        # Content rewriting for anti-cache / module freshness
        if path.endswith(".html") or path.endswith(".htm"):
            content = rewrite_html(content)
            ctype = "text/html; charset=utf-8"
        elif path.endswith(".js"):
            content = rewrite_js(path, content)
            ctype = "text/javascript; charset=utf-8"
        else:
            ctype = self.guess_type(path)

        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Last-Modified", self.date_time_string())
        self.end_headers()
        return io.BytesIO(content)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"Iniciando servidor de desarrollo sin caché en http://localhost:{PORT} (Directorio: {DIRECTORY})")
    with ThreadingTCPServer(("", PORT), NoCacheHTTPRequestHandler) as httpd:
        httpd.serve_forever()
