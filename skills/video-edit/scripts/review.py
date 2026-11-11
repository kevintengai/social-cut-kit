"""Local Editable Source Player."""

import hashlib
import json
import mimetypes
import os
import re
import secrets
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from timeline import EditError, load, prepare


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_server(project, port=0):
    prefix = "/" + secrets.token_urlsafe(24) + "/"
    lock = threading.Lock()
    revision = fingerprint(project)
    document = load(project)
    model = prepare(document, project.parent)
    page = Path(__file__).with_name("review.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_data(self, status, content, mime):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(content)

        def data(self, status, value):
            self.send_data(status, json.dumps(value, ensure_ascii=False).encode(), "application/json")

        def state(self):
            return {"project": document, "model": model, "revision": revision}

        def do_GET(self):
            route = urlsplit(self.path).path
            if not route.startswith(prefix):
                return self.send_error(404)
            route = route[len(prefix):]
            if not route:
                return self.send_data(200, page, "text/html; charset=utf-8")
            if route == "state":
                with lock:
                    return self.data(200, self.state())
            if not route.startswith("media/"):
                return self.send_error(404)
            key = unquote(route[6:])
            with lock:
                asset = model["assets"].get(key)
            if not asset:
                return self.send_error(404)
            try:
                self.stream(Path(asset["path"]))
            except (FileNotFoundError, PermissionError):
                self.send_error(404)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass

        def stream(self, path):
            with path.open("rb") as source:
                size = os.fstat(source.fileno()).st_size
                first, last = 0, size - 1
                requested = self.headers.get("Range")
                if requested:
                    match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested.strip())
                    if not match or not any(match.groups()):
                        return self.send_error(416)
                    left, right = match.groups()
                    if left:
                        first = int(left)
                        last = min(int(right), last) if right else last
                    else:
                        first = max(0, size - int(right))
                    if first > last:
                        return self.send_error(416)
                self.send_response(206 if requested else 200)
                if requested:
                    self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(last - first + 1))
                self.end_headers()
                source.seek(first)
                remaining = last - first + 1
                while remaining:
                    block = source.read(min(remaining, 262144))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)

        def do_POST(self):
            nonlocal revision, document, model
            if self.path != prefix + "save" or self.headers.get("Origin") != self.server.origin:
                return self.send_error(403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 5_000_000:
                    return self.send_error(413)
                incoming = json.loads(self.rfile.read(size))
                if not isinstance(incoming, dict) or "project" not in incoming:
                    raise EditError("Send A Project Object.")
                with lock:
                    if fingerprint(project) != revision or incoming.get("revision") != revision:
                        return self.data(409, {"error": "Project Changed. Reopen The Editor To Load The Latest Version."})
                    next_doc = incoming["project"]
                    next_model = prepare(next_doc, project.parent)
                    next_text = json.dumps(next_doc, ensure_ascii=False, indent=2) + "\n"
                    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                                     dir=project.parent, delete=False) as output:
                        staged = Path(output.name)
                    try:
                        staged.write_bytes(next_text.encode())
                        if fingerprint(project) != revision:
                            return self.data(409, {"error": "Project Changed During Save. Reopen The Editor."})
                        os.replace(staged, project)
                    finally:
                        staged.unlink(missing_ok=True)
                    document, model, revision = next_doc, next_model, fingerprint(project)
                    return self.data(200, self.state())
            except (ValueError, OSError, EditError) as exc:
                return self.data(400, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.origin = "http://127.0.0.1:" + str(server.server_port)
    server.url = server.origin + prefix
    return server


def review(project, port, open_tab=True):
    with make_server(project, port) as server:
        print(f"Local Editor {server.url}\nPress Ctrl+C To Close.", flush=True)
        if open_tab:
            webbrowser.open(server.url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
