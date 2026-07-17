"""Local MJPEG stream used to verify live-source reconnect behavior."""

from __future__ import annotations

import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fps", type=float, default=10.0)
    return parser.parse_args()


def make_handler(video_path: str, fps: float):
    class StreamHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/stream.mjpg":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.end_headers()
            capture = cv2.VideoCapture(video_path)
            try:
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    encoded, jpeg = cv2.imencode(".jpg", frame)
                    if not encoded:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    time.sleep(1.0 / fps)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                capture.release()

        def log_message(self, format: str, *args) -> None:
            return

    return StreamHandler


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(args.video, args.fps)
    )
    print(f"Serving http://{args.host}:{args.port}/stream.mjpg", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
