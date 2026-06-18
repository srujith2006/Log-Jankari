import json
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from config import GPS_SERVER_PORT


BASE_URL = f"http://127.0.0.1:{GPS_SERVER_PORT}"


def request(path, method="GET", body=None, content_type="text/plain"):
    data = body.encode("utf-8") if body is not None else None
    req = Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": content_type},
    )
    with urlopen(req, timeout=3) as response:
        return response.status, response.read().decode("utf-8")


def wait_for_server():
    for _ in range(20):
        try:
            request("/")
            return True
        except Exception:
            time.sleep(0.25)
    return False


def print_result(label, path, method="GET", body=None, content_type="text/plain"):
    try:
        status, response_body = request(path, method, body, content_type)
        print(f"{label} -> {status} {response_body}")
    except HTTPError as error:
        print(f"{label} -> {error.code} {error.read().decode('utf-8')}")


def main():
    process = subprocess.Popen(
        [sys.executable, "-u", "gps_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        if not wait_for_server():
            stdout, stderr = process.communicate(timeout=1)
            print("GPS server did not start.")
            print(stdout)
            print(stderr)
            return 1

        print_result("CSV POST", "/gps", "POST", "23.45,67.89,S")
        print_result("JSON POST", "/gps", "POST", json.dumps({"lat": 12.34, "lon": 56.78, "direction": "N"}), "application/json")
        print_result("Form POST", "/gps", "POST", "latitude=17.3850&longitude=78.4867&direction=90", "application/x-www-form-urlencoded")
        print_result("Query GET", "/gps?lat=19.0760&lon=72.8777&direction=W")
        print_result("Uppercase Query GET", "/gps?Latitude=20.5937&Longitude=78.9629&Heading=45")
        print_result("App Inventor POST", "/gps", "POST", "LocationSensor1.Latitude=21.1458&LocationSensor1.Longitude=79.0882")
        print_result("Latest JSON", "/latest")
        return 0
    finally:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        if stdout:
            print("\nServer terminal output:")
            print(stdout)
        if stderr:
            print("\nServer errors:")
            print(stderr)


if __name__ == "__main__":
    raise SystemExit(main())
