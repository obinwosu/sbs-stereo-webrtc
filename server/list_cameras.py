#!/usr/bin/env python3
"""Probe OpenCV capture indexes so you can find the Magewell USB Fusion UVC device."""

from __future__ import annotations

import argparse
import platform

import cv2


def capture_backend():
    if platform.system() == "Darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def list_devices(max_index: int = 10) -> list[dict]:
    backend = capture_backend()
    found = []

    for index in range(max_index):
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            continue

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        ok, frame = cap.read()
        cap.release()

        found.append(
            {
                "index": index,
                "width": width,
                "height": height,
                "fps": fps,
                "readable": bool(ok and frame is not None),
            }
        )

    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-index", type=int, default=10)
    args = parser.parse_args()

    devices = list_devices(args.max_index)
    if not devices:
        print("No capture devices found.")
        print("Check that the USB Fusion is powered, in SBS mode, and connected over USB-C.")
        return

    print("Readable OpenCV capture devices:")
    for device in devices:
        print(
            f"  --device {device['index']}: "
            f"{device['width']}x{device['height']} @ {device['fps']:.1f} fps "
            f"({'frame ok' if device['readable'] else 'opened but no frame'})"
        )
    print()
    print("USB Fusion usually appears as a 1920x1080 UVC webcam.")
    print("Use that index with: python webrtc_sbs_server.py --device N")


if __name__ == "__main__":
    main()
