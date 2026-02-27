# server.py

"""
Local HTTP server that serves genomic data files with CORS headers.

Files are registered by absolute path and assigned a unique token.
Only registered files can be served, preventing arbitrary filesystem access.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

_TORNADO_PREFIX = "/_igv_streamlit/file/"
_TORNADO_ROUTE  = r"/_igv_streamlit/file/(.*)"

_file_registry: dict[str, str] = {}
_registry_lock  = threading.Lock()

# ── standalone server state ───────────────────────────────────────────────────
_standalone_server: ThreadingHTTPServer | None = None
_standalone_thread: threading.Thread    | None = None
_standalone_port:   int | None = None

# ── Tornado injection state ───────────────────────────────────────────────────
_tornado_injected      = False
_tornado_inject_thread: threading.Thread | None = None

# ── MIME helpers ──────────────────────────────────────────────────────────────
_EXTRA_TYPES = {
    ".bam": "application/octet-stream", ".bai": "application/octet-stream",
    ".cram":"application/octet-stream", ".crai":"application/octet-stream",
    ".bcf": "application/octet-stream", ".csi": "application/octet-stream",
    ".tbi": "application/octet-stream", ".vcf": "text/plain",
    ".gff": "text/plain", ".gff3":"text/plain",  ".gtf": "text/plain",
    ".bed": "text/plain", ".fasta":"text/plain",  ".fa":  "text/plain",
    ".fai": "text/plain", ".gz":  "application/gzip",
}

def _get_mime(path: str) -> str:
    for ext, mime in _EXTRA_TYPES.items():
        if path.endswith(ext):
            return mime
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


# ── shared file-serving logic ─────────────────────────────────────────────────
def _stream_file(token: str, range_header: str | None, write_fn, head_only: bool):
    """
    Resolves token, handles Range, calls write_fn(chunk) for body bytes.
    Returns a metadata dict, or None if the token is unknown (caller should 404).
    """
    with _registry_lock:
        file_path = _file_registry.get(token)

    if file_path is None or not os.path.isfile(file_path):
        return None

    file_size = os.path.getsize(file_path)
    start, end, partial = 0, file_size - 1, False

    if range_header:
        try:
            spec = range_header.strip().removeprefix("bytes=")
            s, _, e = spec.partition("-")
            start = int(s) if s.strip() else 0
            end   = int(e) if e.strip() else file_size - 1
            start = max(0, min(start, file_size - 1))
            end   = max(start, min(end, file_size - 1))
            partial = True
        except Exception:
            return {"error": 400}

    content_length = end - start + 1
    meta = {
        "status":         206 if partial else 200,
        "mime":           _get_mime(file_path),
        "content_length": content_length,
        "partial":        partial,
        "start":          start,
        "end":            end,
        "file_size":      file_size,
    }

    if not head_only:
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    write_fn(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    return meta


# ── standalone HTTP server (for localhost) ────────────────────────────────────
class _CORSHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",   "*")
        self.send_header("Access-Control-Allow-Methods",  "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",  "Range, Content-Type")
        self.send_header("Access-Control-Expose-Headers",
                         "Content-Range, Content-Length, Accept-Ranges")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_HEAD(self): self._handle(head_only=True)
    def do_GET(self):  self._handle(head_only=False)

    def _handle(self, head_only: bool):
        parts = self.path.split("?")[0].strip("/").split("/")
        if len(parts) != 2 or parts[0] != "file":
            self.send_error(404); return

        chunks = []
        meta = _stream_file(
            parts[1],
            self.headers.get("Range"),
            chunks.append,
            head_only,
        )
        if meta is None:
            self.send_error(404); return
        if "error" in meta:
            self.send_error(meta["error"]); return

        self.send_response(meta["status"])
        self.send_header("Content-Type",   meta["mime"])
        self.send_header("Content-Length", str(meta["content_length"]))
        self.send_header("Accept-Ranges",  "bytes")
        if meta["partial"]:
            self.send_header("Content-Range",
                f"bytes {meta['start']}-{meta['end']}/{meta['file_size']}")
        self._cors()
        self.end_headers()
        if not head_only:
            for c in chunks:
                try:    self.wfile.write(c)
                except: break


def _start_standalone() -> int:
    global _standalone_server, _standalone_thread, _standalone_port
    if _standalone_server:
        return _standalone_port
    with socket.socket() as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    _standalone_server = ThreadingHTTPServer(("127.0.0.1", port), _CORSHandler)
    _standalone_port   = port
    _standalone_thread = threading.Thread(
        target=_standalone_server.serve_forever, daemon=True)
    _standalone_thread.start()
    logger.info("igv-streamlit: standalone file server started on port %d", port)
    return port


# ── Tornado injection (for cloud deployments) ─────────────────────────────────
def _make_tornado_handler():
    import tornado.web

    class _FileHandler(tornado.web.RequestHandler):
        def set_default_headers(self):
            self.set_header("Access-Control-Allow-Origin",   "*")
            self.set_header("Access-Control-Allow-Methods",  "GET, HEAD, OPTIONS")
            self.set_header("Access-Control-Allow-Headers",  "Range, Content-Type")
            self.set_header("Access-Control-Expose-Headers",
                            "Content-Range, Content-Length, Accept-Ranges")

        def options(self, token): self.set_status(200)
        def head(self, token):    self._serve(token, head_only=True)
        def get(self, token):     self._serve(token, head_only=False)

        def _serve(self, token, head_only):
            meta = _stream_file(token, self.request.headers.get("Range"),
                                self.write, head_only)
            if meta is None:
                self.set_status(404); return
            if "error" in meta:
                self.set_status(meta["error"]); return
            self.set_status(meta["status"])
            self.set_header("Content-Type",   meta["mime"])
            self.set_header("Content-Length", str(meta["content_length"]))
            self.set_header("Accept-Ranges",  "bytes")
            if meta["partial"]:
                self.set_header("Content-Range",
                    f"bytes {meta['start']}-{meta['end']}/{meta['file_size']}")

    return _FileHandler


def _try_inject_tornado() -> bool:
    global _tornado_injected
    if _tornado_injected:
        return True

    # Small delay so Streamlit finishes its own startup before we walk its
    # internals. Runs in a background thread so it never blocks the app.
    import time
    time.sleep(1)

    tornado_app = None

    # Strategy 1: Streamlit's Server singleton (try multiple known attr paths)
    try:
        from streamlit.web.server.server import Server
        server = getattr(Server, "_singleton", None) or Server.get_current()
        if server:
            for dotpath in (
                "_runtime._server.app",
                "_runtime._server._app",
                "_server.app",
                "_server._app",
                "app",
            ):
                try:
                    obj = server
                    for attr in dotpath.split("."):
                        obj = getattr(obj, attr)
                    tornado_app = obj
                    break
                except AttributeError:
                    continue
    except Exception:
        pass

    # Strategy 2: walk the IOLoop's running HTTP servers via asyncio internals
    if tornado_app is None:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            for obj in getattr(loop, "_servers", {}).values():
                if hasattr(obj, "request_callback"):
                    tornado_app = obj.request_callback
                    break
        except Exception:
            pass

    if tornado_app is None:
        logger.debug("igv-streamlit: could not locate Tornado app — cloud file serving unavailable")
        return False

    try:
        existing = [str(r.regex.pattern)
                    for r in getattr(tornado_app, "wildcard_router", tornado_app).rules]
        if any(_TORNADO_ROUTE in p for p in existing):
            _tornado_injected = True
            return True
        tornado_app.add_handlers(r".*", [(_TORNADO_ROUTE, _make_tornado_handler())])
        _tornado_injected = True
        logger.info("igv-streamlit: Tornado route registered at %s", _TORNADO_PREFIX)
        return True
    except Exception as exc:
        logger.debug("igv-streamlit: Tornado injection failed: %s", exc)
        return False


def _ensure_tornado_injection():
    """Fire-and-forget Tornado injection in a background thread."""
    global _tornado_inject_thread
    if _tornado_injected:
        return
    if _tornado_inject_thread and _tornado_inject_thread.is_alive():
        return
    _tornado_inject_thread = threading.Thread(
        target=_try_inject_tornado, daemon=True)
    _tornado_inject_thread.start()


# ── Public API ────────────────────────────────────────────────────────────────
def register_file(file_path: str) -> str:
    """
    Register a local file and return a sentinel string that the JS component
    resolves to the correct URL at runtime:

      - localhost → ``http://127.0.0.1:<port>/file/<token>``  (standalone server)
      - cloud     → ``/_igv_streamlit/file/<token>``          (Tornado-injected route)
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    port = _start_standalone()
    _ensure_tornado_injection()  # non-blocking, background thread

    with _registry_lock:
        for token, rp in _file_registry.items():
            if rp == file_path:
                return f"__igv__{port}__{token}"
        token = uuid.uuid4().hex
        _file_registry[token] = file_path

    return f"__igv__{port}__{token}"


def get_server_port() -> int | None:
    return _standalone_port