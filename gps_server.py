import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    from config import GPS_SERVER_PORT
except ImportError:
    GPS_SERVER_PORT = 5000


latest_gps = {
    "latitude": 0.0,
    "longitude": 0.0,
    "direction": "0",
}


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def first_value(values, *keys):
    normalized = {key.lower(): value for key, value in values.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value:
            return value[0]
    return None


def parse_gps_values(latitude, longitude, direction="0"):
    if latitude in (None, "") or longitude in (None, ""):
        raise ValueError("Latitude and longitude are required")

    return {
        "latitude": float(str(latitude).strip()),
        "longitude": float(str(longitude).strip()),
        "direction": str(direction or "0").strip(),
    }


def parse_gps_payload(payload, query_values=None, content_type=""):
    query_values = query_values or {}

    if query_values:
        latitude = first_value(query_values, "lat", "latitude")
        longitude = first_value(query_values, "lon", "lng", "long", "longitude")
        direction = first_value(query_values, "dir", "direction", "heading", "bearing") or "0"

        if latitude and longitude is None and "," in latitude:
            parts = [part.strip() for part in latitude.split(",")]
            if len(parts) == 2:
                latitude, longitude = parts
            elif len(parts) == 3:
                latitude, longitude, direction = parts

        return parse_gps_values(latitude, longitude, direction)

    if not payload:
        raise ValueError("Expected: latitude,longitude,direction")

    if "application/json" in content_type:
        data = json.loads(payload)
        return parse_gps_values(
            data.get("lat", data.get("latitude")),
            data.get("lon", data.get("lng", data.get("long", data.get("longitude")))),
            data.get("dir", data.get("direction", data.get("heading", data.get("bearing", "0")))),
        )

    if "=" in payload:
        form_values = parse_qs(payload)
        latitude = first_value(form_values, "lat", "latitude", "LocationSensor1.Latitude")
        longitude = first_value(
            form_values,
            "lon",
            "lng",
            "long",
            "longitude",
            "LocationSensor1.Longitude",
        )
        direction = first_value(
            form_values,
            "dir",
            "direction",
            "heading",
            "bearing",
            "LocationSensor1.Heading",
        ) or "0"
        return parse_gps_values(latitude, longitude, direction)

    parts = [part.strip() for part in payload.split(",")]
    if len(parts) == 2:
        parts.append("0")
    if len(parts) != 3:
        raise ValueError("Expected: latitude,longitude,direction")

    return parse_gps_values(parts[0], parts[1], parts[2])


def print_gps(gps_data):
    print(json.dumps(gps_data), flush=True)
    print(f"Latitude  : {gps_data['latitude']}", flush=True)
    print(f"Longitude : {gps_data['longitude']}", flush=True)
    print(f"Direction : {gps_data['direction']}", flush=True)
    print("-" * 40, flush=True)


class GPSRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path.rstrip("/") != "/gps":
            self.send_text("Not found", status=404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length).decode("utf-8").strip()

        print(f"Received: {payload}", flush=True)

        try:
            gps_data = parse_gps_payload(
                payload,
                query_values=parse_qs(parsed_url.query),
                content_type=self.headers.get("Content-Type", ""),
            )
        except (json.JSONDecodeError, ValueError) as error:
            self.send_text(f"Invalid GPS data. {error}", status=400)
            return

        latest_gps.update(gps_data)
        print_gps(latest_gps)
        self.send_json(latest_gps)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/") or "/"
        if path == "/gps":
            try:
                gps_data = parse_gps_payload("", query_values=parse_qs(parsed_url.query))
            except ValueError as error:
                self.send_text(f"Invalid GPS data. {error}", status=400)
                return

            latest_gps.update(gps_data)
            print_gps(latest_gps)
            self.send_json(latest_gps)
            return

        if path in ("/latest", "/gps.json"):
            self.send_json(latest_gps)
            return

        if path == "/":
            self.send_json(
                {
                    "status": "running",
                    "send_gps_to": "/gps",
                    "latest_json": "/latest",
                    "format": "latitude,longitude,direction",
                    "latest_gps": latest_gps,
                }
            )
            return

        self.send_text("Not found", status=404)

    def log_message(self, format, *args):
        return

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    try:
        server = ReusableThreadingHTTPServer(("0.0.0.0", GPS_SERVER_PORT), GPSRequestHandler)
    except OSError as error:
        print(f"Could not start GPS server on port {GPS_SERVER_PORT}: {error}", flush=True)
        print("Close the old server terminal or change GPS_SERVER_PORT, then run again.", flush=True)
    else:
        local_ip = get_local_ip()
        print(f"GPS server listening on http://0.0.0.0:{GPS_SERVER_PORT}", flush=True)
        print(f"Local test URL: http://127.0.0.1:{GPS_SERVER_PORT}/gps", flush=True)
        print(f"Phone/App URL: http://{local_ip}:{GPS_SERVER_PORT}/gps", flush=True)
        print(f"Latest JSON: http://127.0.0.1:{GPS_SERVER_PORT}/latest", flush=True)
        print("Send data as: latitude,longitude,direction", flush=True)
        server.serve_forever()
