#!/usr/bin/env python3
"""Prepare a Magewell USB Fusion for side-by-side stereo capture.

Uses the USB Fusion HTTP API (firmware 2.4.68+ / V2.0 paths for 2.6.0+):
login, keep the unit awake, confirm HDMI 1/2 lock, switch to SBS, and
report the USB-C UVC output the WebRTC server should capture.

Default AP address is http://192.168.66.1. On Ethernet or USB NET, use
the Fusion's actual IPv4 address instead.

Password is sent as SHA-256 hex, matching the Magewell API agreement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

SIGNAL_LOCKED = 3
TEMPLATE_SBS = 1

# Front-panel buttons, 1-based, from the USB Fusion quick start guide.
BUTTON_HDMI_1 = 1
BUTTON_HDMI_2 = 2
BUTTON_WEBCAM = 3
BUTTON_PIP = 4
BUTTON_SBS = 5

SIGNAL_LABELS = {
    0: "no signal",
    1: "unsupported",
    2: "locking",
    3: "locked",
}


class FusionError(RuntimeError):
    pass


class FusionClient:
    def __init__(self, host: str, timeout: float = 8.0):
        self.base = host.rstrip("/")
        if not self.base.startswith("http"):
            self.base = "http://" + self.base
        self.timeout = timeout
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def _url(self, path: str) -> str:
        return self.base + path

    def post(self, path: str, body=None) -> dict:
        data = b"" if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self._url(path),
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FusionError(f"HTTP {exc.code} for {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise FusionError(f"Could not reach {self.base}: {exc.reason}") from exc

        if not raw.strip():
            return {}
        payload = json.loads(raw)
        status = payload.get("status", payload.get("result", 0))
        if status not in (0, None):
            raise FusionError(f"{path} failed: {payload}")
        return payload

    def get(self, path: str) -> dict:
        request = urllib.request.Request(self._url(path), method="GET")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FusionError(f"HTTP {exc.code} for {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise FusionError(f"Could not reach {self.base}: {exc.reason}") from exc
        return json.loads(raw) if raw.strip() else {}

    def ping(self) -> dict:
        return self.post("/api/ping")

    def login(self, username: str, password: str) -> dict:
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return self.post("/api/user/login", {"username": username, "password": digest})

    def block_sleep(self, block: bool = True) -> dict:
        return self.post("/mwapi/V2.0/general/block-goto-sleep", {"block": 1 if block else 0})

    def summary(self) -> dict:
        return self.post("/mwapi/V2.0/dashboard/get-summary-info")

    def usb_out(self) -> dict:
        return self.post("/mwapi/V2.0/output/get-usb-output-config")

    def scenes(self) -> dict:
        return self.post("/mwapi/V2.0/scene/get-scenes-list")

    def switch_scene(self, scene_id: int) -> dict:
        return self.post("/mwapi/V2.0/scene/switch-scene", {"sceneId": scene_id})

    def press_button(self, button: int) -> dict:
        return self.get(f"/mwapi/V2.0/button/action/{button}")

    def long_press_button(self, button: int) -> dict:
        return self.get(f"/mwapi/V2.0/button/long-press/{button}")


def format_signal(state: dict | None) -> str:
    state = state or {}
    status = state.get("status")
    label = SIGNAL_LABELS.get(status, f"unknown ({status})")
    width = state.get("width")
    height = state.get("height")
    field_rate = state.get("field-rate")
    fps = (field_rate / 100.0) if isinstance(field_rate, (int, float)) and field_rate > 0 else None
    size = f"{width}x{height}" if width and height and width > 0 else "n/a"
    rate = f"{fps:.1f} fps" if fps else "n/a"
    return f"{label}, {size}, {rate}"


def find_sbs_scene(scene_payload: dict) -> dict | None:
    info = scene_payload.get("info") or {}
    for scene in info.get("sceneList") or []:
        if scene.get("template") == TEMPLATE_SBS:
            return scene
    return None


def print_status(client: FusionClient) -> int:
    summary = client.summary()
    device = summary.get("device") or {}
    usb = summary.get("out") or {}

    hdmi1 = device.get("input-hdmi-1-state") or {}
    hdmi2 = device.get("input-hdmi-2-state") or {}

    print(f"Fusion: {client.base}")
    print(f"  HDMI 1: {format_signal(hdmi1)}")
    print(f"  HDMI 2: {format_signal(hdmi2)}")
    print(
        f"  USB-C UVC: {usb.get('video-width')}x{usb.get('video-height')} "
        f"{usb.get('video-format')} @ {(usb.get('video-field-rate') or 0) / 100:.1f} fps"
    )
    print(f"  USB link: {usb.get('speed')}")
    print(f"  UVC running: {usb.get('uvc-running')}")

    ready = hdmi1.get("status") == SIGNAL_LOCKED and hdmi2.get("status") == SIGNAL_LOCKED
    if not ready:
        print("Both HDMI inputs are not locked. Check the DVI-HDMI cables from the console.")
        return 1

    if usb.get("speed") == "disconnected":
        print("USB-C output is disconnected. Plug Fusion USB-C into the Mac.")
        return 1

    print("Both console eyes are locked. Fusion is ready for SBS capture.")
    return 0


def activate_sbs(client: FusionClient, button: int) -> None:
    scenes = client.scenes()
    scene = find_sbs_scene(scenes)
    if scene:
        client.switch_scene(scene["id"])
        print(f"Switched to SBS scene '{scene.get('name')}' (id {scene['id']}).")
        return

    client.press_button(button)
    print(f"No saved SBS scene found. Triggered front-panel SBS button {button}.")
    print("If the split is not 50/50, long-press the SBS button on the device.")


def prepare(client: FusionClient, button: int) -> int:
    client.block_sleep(True)
    print("Sleep blocked while this session is logged in.")
    activate_sbs(client, button)
    return print_status(client)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["ping", "status", "sbs", "prepare"],
        help="ping: reachability. status: HDMI/USB report. sbs: switch layout. prepare: all of the above.",
    )
    parser.add_argument("--host", default=os.environ.get("FUSION_HOST", "192.168.66.1"))
    parser.add_argument("--username", default=os.environ.get("FUSION_USERNAME", "Admin"))
    parser.add_argument(
        "--password",
        default=os.environ.get("FUSION_PASSWORD", ""),
        help="Plaintext Fusion password. It is SHA-256 hashed before login. Or set FUSION_PASSWORD.",
    )
    parser.add_argument(
        "--sbs-button",
        type=int,
        default=BUTTON_SBS,
        help="Front-panel SBS button index (default 5).",
    )
    return parser


def main():
    args = build_parser().parse_args()
    client = FusionClient(args.host)

    if args.command == "ping":
        client.ping()
        print(f"Fusion reachable at {client.base}")
        return

    if not args.password:
        print("Set --password or FUSION_PASSWORD.", file=sys.stderr)
        sys.exit(2)

    client.login(args.username, args.password)

    if args.command == "status":
        sys.exit(print_status(client))
    if args.command == "sbs":
        activate_sbs(client, args.sbs_button)
        sys.exit(print_status(client))
    if args.command == "prepare":
        sys.exit(prepare(client, args.sbs_button))


if __name__ == "__main__":
    main()
