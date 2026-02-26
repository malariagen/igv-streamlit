"""
Local HTTP server that serves genomic data files with CORS headers.

Files are registered by absolute path and assigned a unique token.
Only registered files can be served, preventing arbitrary filesystem access.
"""

import os
import threading
import socket
import uuid
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── global state ──────────────────────────────────────────────────────────────
_server: HTTPServer | None = None
_server_thread: threading.Thread | None = None
_server_port: int | None = None
_file_registry: dict[str, str] = {}   # token → absolute path
_registry_lock = threading.Lock()

# ── MIME type helpers ─────────────────────────────────────────────────────────
_EXTRA_TYPES = {
    ".bam":  "application/octet-stream",
    ".bai":  "application/octet-stream",
    ".cram": "application/octet-stream",
    ".crai": "application/octet-stream",
    ".bcf":  "application/octet-stream",
    ".csi":  "application/octet-stream",
    ".tbi":  "application/octet-stream",
    ".vcf":  "text/plain",
    ".gff":  "text/plain",
    ".gff3": "text/plain",
    ".gtf":  "text/plain",
    ".bed":  "text/plain",
    ".fasta": "text/plain",
    ".fa":   "text/plain",
    ".fai":  "text/plain",
    ".gz":   "application/gzip",
}


def _get_mime(path: str) -> str:
    for ext, mime in _EXTRA_TYPES.items():
        if path.endswith(ext):
            return mime
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


# ── Request handler ───────────────────────────────────────────────────────────
class _CORSHandler(BaseHTTPRequestHandler):
    """Serves registered files with full CORS + range-request support."""

    def log_message(self, format, *args):  # silence default logging
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Range, Content-Type, Accept-Encoding",
        )
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self._handle_request(head_only=True)

    def do_GET(self):
        self._handle_request(head_only=False)

    def _handle_request(self, head_only: bool):
        # Path format: /file/<token>
        path = self.path.split("?")[0]  # strip query string
        parts = path.strip("/").split("/")

        if len(parts) != 2 or parts[0] != "file":
            self.send_error(404, "Not found")
            return

        token = parts[1]
        with _registry_lock:
            file_path = _file_registry.get(token)

        if file_path is None:
            self.send_error(404, "Unknown token")
            return

        if not os.path.isfile(file_path):
            self.send_error(404, f"File not found: {file_path}")
            return

        file_size = os.path.getsize(file_path)
        mime_type = _get_mime(file_path)

        # Parse Range header for partial content (required by igv.js for BAM/CRAM)
        range_header = self.headers.get("Range")
        start = 0
        end = file_size - 1
        partial = False

        if range_header:
            try:
                range_spec = range_header.strip().replace("bytes=", "")
                s, e = range_spec.split("-")
                start = int(s) if s else 0
                end = int(e) if e else file_size - 1
                partial = True
            except Exception:
                self.send_error(400, "Invalid Range header")
                return

        content_length = end - start + 1

        if partial:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        else:
            self.send_response(200)

        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self._send_cors_headers()
        self.end_headers()

        if head_only:
            return

        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            chunk_size = 65536
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


# ── Server lifecycle ──────────────────────────────────────────────────────────
def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_server() -> int:
    """Start the background HTTP server. Returns the port number."""
    global _server, _server_thread, _server_port

    if _server is not None:
        return _server_port

    port = _find_free_port()
    _server = HTTPServer(("127.0.0.1", port), _CORSHandler)
    _server_port = port

    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()
    return port


def ensure_server_running() -> int:
    """Ensure the file server is running and return its port."""
    global _server_port
    if _server is None:
        _start_server()
    return _server_port


def register_file(file_path: str) -> str:
    """
    Register a local file and return a URL that igv.js can fetch.

    Args:
        file_path: Absolute path to the file.

    Returns:
        A localhost URL string.
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    port = ensure_server_running()

    # Check if already registered (dedup by path)
    with _registry_lock:
        for token, registered_path in _file_registry.items():
            if registered_path == file_path:
                return f"http://127.0.0.1:{port}/file/{token}"
        token = uuid.uuid4().hex
        _file_registry[token] = file_path

    return f"http://127.0.0.1:{port}/file/{token}"


def get_server_port() -> int | None:
    return _server_port
