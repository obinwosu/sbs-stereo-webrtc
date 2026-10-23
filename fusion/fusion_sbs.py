"""Prepare a Magewell USB Fusion for side-by-side stereo capture.

Uses the USB Fusion HTTP API (firmware 2.4.68+; V2.0 paths for 2.6.0+):
- login
- keep the device awake
- confirm HDMI 1 / HDMI 2 are locked
- switch to an SBS scene, or press the physical SBS button via API
- report USB-C UVC output status

Default AP address is 192.168.66.1. Ethernet or USB NET may use another IP.
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

SIGNAL_STATUS = {
    0: "no signal",
    1: "unsupported",
    2: "locking",
    3: "locked",
}

SCENE_TEMPLATE = {
    0: "picture-in-picture",
    1: "side-by-side",
    2: "single",
}

# USB Fusion front-panel buttons, left to right.
BUTTONS = {
    1: "HDMI 1",
    2: "HDMI 2",
    3: "WEB CAMERA 3",
    4: "PIP",
    5: "SBS",
}


class FusionClient:
    def __init__(self, host: str, username: str, password: str, api_prefix: str):
        self.base = f"http://{host}"
        self.username = username
        self.password = password
        self.api_prefix = api_prefix.rstrip("/")
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def _url(self, path: str) -> str:
        if path.startswith("/"):
            return self.base + path
        return f"{self.base}{self.api_prefix}/{path}"

    def request(self, path: str, body=None, method="POST"):
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        elif method == "POST":
            data = b"{}"

        req = urllib.request.Request(
            self._url(path),
            data=data,
            method=method,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with self.opener.open(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{path} failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Fusion at {self.base}: {exc.reason}") from exc

        if not raw:
            return {}
        return json.loads(raw)

    def ping(self):
        return self.request("/api/ping", body=None)

    def login(self):
        digest = hashlib.sha256(self.password.encode("utf-8")).hexdigest()
        result = self.request(
            "/api/user/login",
            {"username": self.username, "password": digest},
        )
        status = result.get("status", result.get("result"))
        if status not in (0, None):
            raise RuntimeError(f"Login failed: {result}")
        return result

    def block_sleep(self, block=True):
        return self.request("general/block-goto-sleep", {"block": 1 if block else 0})

    def summary(self):
        return self.request("dashboard/get-summary-info")

    def scenes(self):
        return self.request("scene/get-scenes-list")

    def switch_scene(self, scene_id: int):
        return self.request("scene/switch-scene", {"sceneId": scene_id})

    def press_button(self, number: int, long_press=False):
        action = "long-press" if long_press else "action"
        return self.request(f"button/{action}/{number}", body=None)

    def usb_output(self):
        return self.request("output/get-usb-output-config")


def describe_signal(state: dict) -> str:
    if not state:
        return "missing"
    code = state.get("status", 0)
    label = SIGNAL_STATUS.get(code, f"unknown ({code})")
    width = state.get("width")
    height = state.get("height")
    rate = state.get("field-rate")
    fps = f"{rate / 100:.1f} fps" if isinstance(rate, (int, float)) and rate > 0 else "n/a"
    return f"{label} {width}x{height} {fps}"


def print_status(client: FusionClient):
    info = client.summary()
    device = info.get("device", {})
    out = info.get("out", {})

    print("HDMI 1:", describe_signal(device.get("input-hdmi-1-state")))
    print("HDMI 2:", describe_signal(device.get("input-hdmi-2-state")))
    print("USB-C speed:", out.get("speed"))
    print("UVC running:", out.get("uvc-running"))
    print(
        "USB-C video:",
        f"{out.get('video-width')}x{out.get('video-height')} "
        f"{out.get('video-format')} {out.get('video-scan')}",
    )
    dropped = out.get("video-drop-frames")
    if dropped:
        print("Dropped frames last second:", dropped)
    return info


def find_sbs_scene(client: FusionClient):
    payload = client.scenes()
    info = payload.get("info") or payload
    scenes = info.get("sceneList") or []
    for scene in scenes:
        if scene.get("template") == 1:
            return scene
    return None


def prepare(client: FusionClient, sbs_button: int):
    print("Logging in...")
    client.login()
    client.block_sleep(True)
    print("Sleep blocked.")

    info = print_status(client)
    device = info.get("device", {})
    hdmi1 = (device.get("input-hdmi-1-state") or {}).get("status")
    hdmi2 = (device.get("input-hdmi-2-state") or {}).get("status")
    if hdmi1 != 3 or hdmi2 != 3:
        print(
            "Warning: both HDMI inputs should be locked (status 3) "
            "before SBS stereo will look correct."
        )

    scene = find_sbs_scene(client)
    if scene:
        print(f"Switching to SBS scene {scene.get('id')} ({scene.get('name')})")
        print(client.switch_scene(scene["id"]))
    else:
        print(f"No saved SBS scene found. Pressing button {sbs_button} ({BUTTONS.get(sbs_button, '?')})")
        print(client.press_button(sbs_button))

    print("\nUSB output after SBS switch:")
    print_status(client)
    print(
        "\nNext: run server/webrtc_sbs_server.py --list-devices, "
        "then start the server on the Fusion UVC device."
    )


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("FUSION_HOST", "192.168.66.1"))
    parser.add_argument("--username", default=os.environ.get("FUSION_USERNAME", "Admin"))
    parser.add_argument(
        "--password",
        default=os.environ.get("FUSION_PASSWORD", ""),
        help="Plaintext Fusion password. It is SHA-256 hashed before login.",
    )
    parser.add_argument(
        "--api-prefix",
        default="/mwapi/V2.0",
        help="Use /mwapi for firmware 2.5 and below",
    )
    parser.add_argument(
        "--sbs-button",
        type=int,
        default=5,
        help="Front-panel button index for SBS. Default 5.",
    )
    parser.add_argument(
        "command",
        choices=["ping", "status", "sbs", "scenes", "prepare"],
        help="ping: reachability. status: HDMI/USB. sbs: switch. scenes: list. prepare: full setup.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    if args.command != "ping" and not args.password:
        print("Set --password or FUSION_PASSWORD.", file=sys.stderr)
        sys.exit(2)

    client = FusionClient(args.host, args.username, args.password, args.api_prefix)

    if args.command == "ping":
        print(client.ping())
        return

    client.login()

    if args.command == "status":
        print_status(client)
        return

    if args.command == "scenes":
        payload = client.scenes()
        info = payload.get("info") or payload
        for scene in info.get("sceneList") or []:
            template = SCENE_TEMPLATE.get(scene.get("template"), scene.get("template"))
            print(f"{scene.get('id')}\t{scene.get('name')}\t{template}")
        return

    if args.command == "sbs":
        scene = find_sbs_scene(client)
        if scene:
            print(client.switch_scene(scene["id"]))
        else:
            print(client.press_button(args.sbs_button))
        return

    if args.command == "prepare":
        prepare(client, args.sbs_button)


if __name__ == "__main__":
    main()
