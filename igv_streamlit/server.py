# server.py

"""
Local HTTP server that serves genomic data files with CORS headers.

Files are registered by absolute path and assigned a unique token.
Only registered files can be served, preventing arbitrary filesystem access.

Note: local file serving only works when running Streamlit locally.
For cloud deployments, use remote URLs (url/indexURL) instead of local paths.
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

_file_registry: dict[str, str] = {}
_registry_lock  = threading.Lock()

_standalone_server: ThreadingHTTPServer | None = None
_standalone_thread: threading.Thread    | None = None
_standalone_port:   int | None = None

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

        token = parts[1]
        with _registry_lock:
            file_path = _file_registry.get(token)

        if file_path is None or not os.path.isfile(file_path):
            self.send_error(404); return

        file_size = os.path.getsize(file_path)
        mime_type = _get_mime(file_path)
        start, end, partial = 0, file_size - 1, False

        range_header = self.headers.get("Range")
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
                self.send_error(400); return

        content_length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type",   mime_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges",  "bytes")
        if partial:
            self.send_header("Content-Range",
                f"bytes {start}-{end}/{file_size}")
        self._cors()
        self.end_headers()

        if head_only:
            return

        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


def _start_server() -> int:
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
    logger.info("igv-streamlit: file server started on port %d", port)
    return port


def register_file(file_path: str) -> str:
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    port = _start_server()

    with _registry_lock:
        for token, rp in _file_registry.items():
            if rp == file_path:
                return f"http://127.0.0.1:{port}/file/{token}"
        token = uuid.uuid4().hex
        _file_registry[token] = file_path

    return f"http://127.0.0.1:{port}/file/{token}"


def get_server_port() -> int | None:
    return _standalone_port