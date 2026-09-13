"""Loopback-only HTTP transport for the local game."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .engine import CROPS, MISSIONS, GameError, new_state
from .interpreter import run_script
from .saves import validate_save
from .world import create_game, validate_game
from .factory import CATALOG, MISSIONS as FACTORY_MISSIONS, new_factory, Factory

STATIC = Path(__file__).resolve().parent.parent / "static"
EXAMPLES = STATIC.parent / "examples"
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/farm.js": ("farm.js", "text/javascript"), "/factory-ui.js": ("factory-ui.js", "text/javascript"), "/style.css": ("style.css", "text/css"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}
MAX_BODY = 100000
MAX_SAVE_BODY = 300000


class GameHandler(BaseHTTPRequestHandler):
    server_version = "Sprout/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def trusted_request(self):
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host not in allowed or (origin is not None and origin != f"http://{host}"):
            self.respond(403, {"error": "Use this game from its local browser address."})
            return False
        return True

    def respond(self, status, data, content_type="application/json"):
        body = json.dumps(data, allow_nan=False).encode() if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.trusted_request():
            return
        path = urlsplit(self.path).path
        if path == "/api/bootstrap":
            examples = {name: (EXAMPLES / (filename + ".py")).read_text() for name, filename in {
                "starter": "starter", "full_field": "full_field", "smart_farmer": "smart_farmer", "carrots": "carrots"
            }.items()}
            factory_examples = {name: (EXAMPLES / f"factory_{name}.py").read_text() for name in ("starter", "harvest", "bakery", "orders")}
            return self.respond(200, {"state": new_state(), "crops": CROPS, "missions": MISSIONS, "examples": examples,
                                     "chapters": {"classic": {"title": "Home farm", "state": new_state(), "missions": MISSIONS, "examples": examples},
                                                  "factory": {"title": "The Breadworks", "state": new_factory(), "missions": FACTORY_MISSIONS, "examples": factory_examples, "catalog": CATALOG}}})
        if path in ASSETS:
            filename, mime = ASSETS[path]
            return self.respond(200, (STATIC / filename).read_bytes(), mime)
        self.respond(404, {"error": "Not found."})

    def do_POST(self):
        if not self.trusted_request():
            return
        if self.headers.get_content_type() != "application/json":
            return self.respond(415, {"error": "Expected application/json."})
        try:
            path = urlsplit(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            limit = MAX_SAVE_BODY if path == "/api/save/validate" else MAX_BODY
            if not 0 < length <= limit:
                return self.respond(413, {"error": f"Request must be between 1 and {limit:,} bytes."})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise GameError("Expected a JSON object.")
            if path == "/api/save/validate":
                return self.respond(200, {"save": validate_save(payload.get("save"))})
            if path == "/api/validate":
                return self.respond(200, {"state": validate_game(payload.get("state"))})
            if path == "/api/run":
                state = validate_game(payload.get("state"))
                return self.respond(200, run_script(payload.get("code"), state))
            if path == "/api/unlock":
                farm = create_game(validate_game(payload.get("state")))
                message = farm.unlock(payload.get("item"))
                return self.respond(200, {"state": farm.snapshot(), "message": message})
            if path == "/api/order":
                farm = create_game(validate_game(payload.get("state")))
                if not isinstance(farm, Factory):
                    raise GameError("Delivery orders belong to the Breadworks chapter.")
                message = farm.start_order()
                return self.respond(200, {"state": farm.snapshot(), "message": message})
            return self.respond(404, {"error": "Not found."})
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self.respond(400, {"error": str(exc)[:300]})


def create_server(port=8000):
    return ThreadingHTTPServer(("127.0.0.1", port), GameHandler)
