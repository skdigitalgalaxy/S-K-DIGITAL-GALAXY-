import base64
import hashlib
import json
import ipaddress
import logging
import mimetypes
import os
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
APP_ORIGIN = os.environ.get("APP_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
ORIGIN_PARTS = urlsplit(APP_ORIGIN)
if (
    ORIGIN_PARTS.scheme not in {"http", "https"}
    or not ORIGIN_PARTS.netloc
    or ORIGIN_PARTS.path
    or ORIGIN_PARTS.query
    or ORIGIN_PARTS.fragment
    or ORIGIN_PARTS.username
    or ORIGIN_PARTS.password
):
    raise RuntimeError("APP_ORIGIN must be an http(s) origin without a path.")

EXPECTED_HOST = ORIGIN_PARTS.netloc.casefold()
TRUSTED_PROXY_IP = os.environ.get("TRUSTED_PROXY_IP", "")
if TRUSTED_PROXY_IP:
    try:
        TRUSTED_PROXY_IP = str(ipaddress.ip_address(TRUSTED_PROXY_IP))
    except ValueError as error:
        raise RuntimeError("TRUSTED_PROXY_IP must be a single IP address.") from error
INQUIRY_TO = os.environ.get("INQUIRY_TO", "sandkdigitalgalaxy@gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SHEETS_WEB_APP_URL = os.environ.get("SHEETS_WEB_APP_URL", "")
SHEETS_WEBHOOK_SECRET = os.environ.get("SHEETS_WEBHOOK_SECRET", "")
MAX_BODY_BYTES = 8192
RATE_WINDOW_SECONDS = 900
RATE_MAX_REQUESTS = 5
RATE_MAX_CLIENTS = 4096
ALLOWED_SERVICES = {
    "Business consulting",
    "Finance and accounting",
    "Software and IT",
    "Marketing and media",
    "Design and content",
    "Data and analytics",
    "Other",
}
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE_PATTERN = re.compile(r"[0-9+().\-\s]*")
STATIC_FILES = {
    "/": ROOT / "index.html",
    "/index.html": ROOT / "index.html",
    "/site.js": ROOT / "site.js",
    "/assets/sk-digital-galaxy-logo.svg": ROOT / "assets" / "sk-digital-galaxy-logo.svg",
}
STYLE_BLOCK = re.search(rb"<style(?:\s[^>]*)?>(.*?)</style>", (ROOT / "index.html").read_bytes(), re.DOTALL)
if STYLE_BLOCK is None:
    raise RuntimeError("The page must contain its trusted stylesheet block.")
STYLE_HASH = base64.b64encode(hashlib.sha256(STYLE_BLOCK.group(1)).digest()).decode("ascii")
RATE_LOCK = threading.Lock()
RATE_REQUESTS = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("sk-galaxy-api")


def _has_unsafe_controls(value, allow_newlines=False):
    allowed = "\n\t" if allow_newlines else ""
    return any(ord(character) < 32 and character not in allowed for character in value)


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not allowed.")
        result[key] = value
    return result


def validate_inquiry(payload):
    if not isinstance(payload, dict):
        raise ValueError("Invalid request.")

    allowed_fields = {"name", "email", "phone", "business", "service", "message", "website"}
    if set(payload) - allowed_fields:
        raise ValueError("Unexpected form fields.")

    values = {}
    limits = {"name": 100, "email": 254, "phone": 40, "business": 140, "service": 80, "message": 4000, "website": 200}
    for field, limit in limits.items():
        value = payload.get(field, "")
        if not isinstance(value, str):
            raise ValueError("Invalid form fields.")
        value = value.strip()
        if len(value) > limit or _has_unsafe_controls(value, allow_newlines=field == "message"):
            raise ValueError("One or more fields are invalid or too long.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("Form fields must contain valid text.") from error
        values[field] = value

    if not values["name"] or not values["email"] or not values["service"] or not values["message"]:
        raise ValueError("Complete all required fields.")
    if not EMAIL_PATTERN.fullmatch(values["email"]):
        raise ValueError("Enter a valid email address.")
    if values["phone"] and not PHONE_PATTERN.fullmatch(values["phone"]):
        raise ValueError("Enter a valid phone number.")
    if values["service"] not in ALLOWED_SERVICES:
        raise ValueError("Select a valid service.")

    return values


def build_inquiry_message(values):
    message = EmailMessage()
    message["Subject"] = "New website enquiry for S&K Digital Galaxy"
    message["From"] = SMTP_USER
    message["To"] = INQUIRY_TO
    message["Reply-To"] = values["email"]
    message.set_content(
        "A new inquiry was submitted through the website.\n\n"
        f"Name: {values['name']}\n"
        f"Email: {values['email']}\n"
        f"Phone: {values['phone'] or 'Not provided'}\n"
        f"Business: {values['business'] or 'Not provided'}\n"
        f"Service: {values['service']}\n\n"
        f"Project details:\n{values['message']}\n"
    )
    return message


def rate_limit_exceeded(client_address, now=None):
    now = time.monotonic() if now is None else now
    cutoff = now - RATE_WINDOW_SECONDS
    with RATE_LOCK:
        recent_requests = [stamp for stamp in RATE_REQUESTS.get(client_address, []) if stamp > cutoff]
        if len(recent_requests) >= RATE_MAX_REQUESTS:
            RATE_REQUESTS[client_address] = recent_requests
            return True
        if client_address not in RATE_REQUESTS and len(RATE_REQUESTS) >= RATE_MAX_CLIENTS:
            for address in list(RATE_REQUESTS):
                if not RATE_REQUESTS[address] or RATE_REQUESTS[address][-1] <= cutoff:
                    del RATE_REQUESTS[address]
            if len(RATE_REQUESTS) >= RATE_MAX_CLIENTS:
                return True
        recent_requests.append(now)
        RATE_REQUESTS[client_address] = recent_requests
    return False


def send_inquiry(values):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("SMTP credentials are not configured.")
    if not EMAIL_PATTERN.fullmatch(SMTP_USER) or not EMAIL_PATTERN.fullmatch(INQUIRY_TO):
        raise RuntimeError("SMTP email configuration is invalid.")

    message = build_inquiry_message(values)
    tls_context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as connection:
        connection.ehlo()
        connection.starttls(context=tls_context)
        connection.ehlo()
        connection.login(SMTP_USER, SMTP_PASSWORD)
        connection.send_message(message)


def append_inquiry_to_google_sheet(values):
    if not SHEETS_WEB_APP_URL or len(SHEETS_WEBHOOK_SECRET) < 32:
        raise RuntimeError("Google Sheets integration is not configured.")

    endpoint = urlsplit(SHEETS_WEB_APP_URL)
    if (
        endpoint.scheme != "https"
        or endpoint.hostname != "script.google.com"
        or not endpoint.path.startswith("/macros/s/")
        or not endpoint.path.endswith("/exec")
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise RuntimeError("Google Sheets endpoint is invalid.")

    sheet_payload = {
        "token": SHEETS_WEBHOOK_SECRET,
        "submitted": True,
        "name": values["name"],
        "email": values["email"],
        "phone": values["phone"],
        "business": values["business"],
        "service": values["service"],
        "message": values["message"],
    }
    request_body = json.dumps(sheet_payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        SHEETS_WEB_APP_URL,
        data=request_body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    tls_context = ssl.create_default_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls_context))
    with opener.open(request, timeout=10) as response:
        response_body = response.read(4097)
    if len(response_body) > 4096:
        raise RuntimeError("Google Sheets returned an oversized response.")
    result = json.loads(response_body.decode("utf-8"))
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError("Google Sheets did not confirm the inquiry.")
    return True


class RequestHandler(BaseHTTPRequestHandler):
    server_version = ""
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def version_string(self):
        return ""

    def log_message(self, format_string, *args):
        request_path = urlsplit(self.path).path
        LOGGER.info("%s %s %s", self.client_address[0], self.command, request_path)

    def send_error(self, code, message=None, explain=None):
        self._send_json(code, {"error": "Request rejected."})

    def _send_response(self, status, body=b"", content_type="application/json; charset=utf-8", extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("X-Permitted-Cross-Domain-Policies", "none")
        self.send_header("Origin-Agent-Cluster", "?1")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            f"default-src 'self'; script-src 'self'; style-src 'self' 'sha256-{STYLE_HASH}'; "
            "img-src 'self'; font-src 'self'; connect-src 'self'; form-action 'self'; "
            "base-uri 'self'; object-src 'none'; frame-ancestors 'none'",
        )
        if APP_ORIGIN.startswith("https://"):
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        for header, value in (extra_headers or {}).items():
            self.send_header(header, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status, data, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_response(status, body, extra_headers=extra_headers)

    def _method_not_allowed(self):
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed."}, {"Allow": "GET, HEAD, POST"})

    def _serve_static(self):
        request_path = unquote(urlsplit(self.path).path)
        file_path = STATIC_FILES.get(request_path)
        if file_path is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
            content_type += "; charset=utf-8"
        self._send_response(HTTPStatus.OK, body, content_type=content_type)

    def do_GET(self):
        self._serve_static()

    def do_HEAD(self):
        self._serve_static()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/inquiries":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        request_origin = self.headers.get("Origin", "").rstrip("/").casefold()
        if self.headers.get("Host", "").casefold() != EXPECTED_HOST or request_origin != APP_ORIGIN.casefold():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Request origin not allowed."})
            return

        if self.headers.get("Content-Encoding", "identity").casefold() != "identity":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Unsupported content encoding."})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold() != "application/json":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Send JSON form data."})
            return
        try:
            body_size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(HTTPStatus.LENGTH_REQUIRED, {"error": "Content length required."})
            return
        if body_size <= 0 or body_size > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Request is too large."})
            return
        if rate_limit_exceeded(self._client_address_for_limits()):
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many requests. Try again later."})
            return

        try:
            request_body = self.rfile.read(body_size)
            if len(request_body) != body_size:
                raise ValueError("Incomplete request body.")
            payload = json.loads(request_body.decode("utf-8"), object_pairs_hook=_unique_json_object)
            values = validate_inquiry(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error) or "Invalid request."})
            return

        if values["website"]:
            self._send_json(HTTPStatus.ACCEPTED, {"message": "Enquiry received.", "sheetSaved": None})
            return

        try:
            send_inquiry(values)
        except Exception as error:
            LOGGER.error("Inquiry email delivery failed (%s).", type(error).__name__)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "We could not send your enquiry. Please email us directly."})
            return

        sheet_saved = None
        try:
            sheet_saved = append_inquiry_to_google_sheet(values)
        except Exception as error:
            LOGGER.error("Google Sheets sync failed (%s).", type(error).__name__)
            self._send_json(
                HTTPStatus.ACCEPTED,
                {"message": "Your enquiry was emailed, but could not be added to the private sheet.", "sheetSaved": False},
            )
            return

        self._send_json(HTTPStatus.ACCEPTED, {"message": "Enquiry received.", "sheetSaved": sheet_saved})

    def do_OPTIONS(self):
        self._method_not_allowed()

    def do_PUT(self):
        self._method_not_allowed()

    def do_PATCH(self):
        self._method_not_allowed()

    def do_DELETE(self):
        self._method_not_allowed()

    def do_TRACE(self):
        self._method_not_allowed()

    def do_CONNECT(self):
        self._method_not_allowed()

    def handle_expect_100(self):
        self._send_json(HTTPStatus.EXPECTATION_FAILED, {"error": "Continue requests are not supported."})
        return False

    def _client_address_for_limits(self):
        peer_address = str(ipaddress.ip_address(self.client_address[0]))
        if not TRUSTED_PROXY_IP or peer_address != TRUSTED_PROXY_IP:
            return peer_address
        try:
            return str(ipaddress.ip_address(self.headers.get("X-Real-IP", "")))
        except ValueError:
            return peer_address


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, server_address, request_handler):
        self.request_slots = threading.BoundedSemaphore(32)
        super().__init__(server_address, request_handler)

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()


def main():
    bind_host = os.environ.get("BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    if bind_host not in {"127.0.0.1", "localhost"} and os.environ.get("ALLOW_NON_LOOPBACK_BIND") != "1":
        raise SystemExit("Non-loopback binding requires ALLOW_NON_LOOPBACK_BIND=1 and a trusted HTTPS reverse proxy.")
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535.")

    with BoundedThreadingHTTPServer((bind_host, port), RequestHandler) as server:
        LOGGER.info("Serving on %s:%s for origin %s", bind_host, port, APP_ORIGIN)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            LOGGER.info("Server stopping.")


if __name__ == "__main__":
    main()