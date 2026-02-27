"""
Local HTTP server that serves genomic data files with CORS headers.

On localhost: a standalone HTTP server binds to a random port on 127.0.0.1.
On cloud:     files are symlinked into static/ and served by Streamlit's
              built-in static file handler (requires enableStaticServing = true
              in .streamlit/config.toml).
"""

from __future__ import annotations

import logging
import mimetypes
import os
import pathlib
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

# Streamlit serves <repo-root>/static/ at /app/static/
# __file__ is <repo>/igv_streamlit/server.py → parent.parent = repo root
_STATIC_DIR = pathlib.Path(__file__).parent.parent / "static"

def _clean_static_dir():
    """Remove any symlinks left over from previous approaches."""
    if not _STATIC_DIR.exists():
        return
    for entry in _STATIC_DIR.iterdir():
        if entry.is_symlink():
            entry.unlink()
            logger.debug("igv-streamlit: removed stale symlink %s", entry.name)

_clean_static_dir()

_file_registry: dict[str, str] = {}
_registry_lock  = threading.Lock()

# ── standalone server state ───────────────────────────────────────────────────
_standalone_server: ThreadingHTTPServer | None = None
_standalone_thread: threading.Thread    | None = None
_standalone_port:   int | None = None

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


# ── standalone HTTP server (localhost) ────────────────────────────────────────
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
        meta   = _stream_file(parts[1], self.headers.get("Range"),
                               chunks.append, head_only)
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


# ── Public API ────────────────────────────────────────────────────────────────
def register_file(file_path: str) -> str:
    """
    Register a local file and return a sentinel string that the JS component
    resolves to the correct URL at runtime:

      - localhost → ``http://127.0.0.1:<port>/file/<token>``  (standalone server)
      - cloud     → ``/app/static/<token>``                   (Streamlit static serving)
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    port = _start_standalone()

    with _registry_lock:
        for token, rp in _file_registry.items():
            if rp == file_path:
                return f"__igv__{port}__{token}"
        token = uuid.uuid4().hex
        _file_registry[token] = file_path

    _STATIC_DIR.mkdir(exist_ok=True)
    dest = _STATIC_DIR / token
    if not dest.exists():
        import shutil
        shutil.copy2(file_path, dest)

    return f"__igv__{port}__{token}"


def get_server_port() -> int | None:
    return _standalone_port