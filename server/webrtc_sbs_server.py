"""Capture a Magewell USB Fusion SBS camera and serve it over WebRTC.

The Fusion already composites left/right into one side-by-side frame.
This server does not split eyes. It streams that single SBS track to a
browser tester or a Unity XR client that samples left/right halves.
"""

import argparse
import asyncio
import platform
import time
from pathlib import Path

import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

pcs = set()
HERE = Path(__file__).resolve().parent


def capture_backend():
    if platform.system() == "Darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def list_capture_devices(max_index=10):
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
        found.append((index, width, height, fps))
        print(f"Device {index}: {width}x{height} @ {fps:.2f} fps")
        cap.release()
    if not found:
        print("No capture devices found.")
    return found


def describe_video_codecs(sdp: str):
    payload_to_codec = {}

    for line in sdp.splitlines():
        if line.startswith("a=rtpmap:"):
            try:
                payload = line.split(":", 1)[1].split(" ", 1)[0]
                codec = line.split(" ", 1)[1]
                payload_to_codec[payload] = codec
            except Exception:
                pass

    video_payloads = []

    for line in sdp.splitlines():
        if line.startswith("m=video"):
            parts = line.split()
            video_payloads = parts[3:]
            break

    codecs = [payload_to_codec.get(p, f"payload {p}") for p in video_payloads]
    return codecs


def force_video_bitrate_in_sdp(sdp: str, bitrate_bps: int) -> str:
    """
    Adds b=AS and b=TIAS lines to the video m-section.
    This is not guaranteed to force encoder behavior, but it is useful
    when sender.setParameters is ignored.
    """
    bitrate_kbps = bitrate_bps // 1000

    lines = sdp.splitlines()
    out = []
    in_video = False
    inserted = False

    for line in lines:
        if line.startswith("m="):
            in_video = line.startswith("m=video")
            inserted = False

        out.append(line)

        if in_video and not inserted and line.startswith("c=IN"):
            out.append(f"b=AS:{bitrate_kbps}")
            out.append(f"b=TIAS:{bitrate_bps}")
            inserted = True

    return "\r\n".join(out) + "\r\n"


async def stats_loop(pc: RTCPeerConnection, label: str = "pc"):
    """
    Prints approximate outbound video bitrate from aiortc stats.
    """
    last_bytes = None
    last_time = None

    while pc.connectionState not in ("closed", "failed", "disconnected"):
        await asyncio.sleep(2)

        try:
            stats = await pc.getStats()
        except Exception as e:
            print(f"[STATS] getStats failed: {e}")
            continue

        now = time.time()

        for report in stats.values():
            if report.type == "outbound-rtp" and getattr(report, "kind", None) == "video":
                bytes_sent = getattr(report, "bytesSent", None)
                packets_sent = getattr(report, "packetsSent", None)

                if bytes_sent is None:
                    continue

                if last_bytes is not None and last_time is not None:
                    delta_bytes = bytes_sent - last_bytes
                    delta_time = now - last_time
                    if delta_time > 0:
                        mbps = (delta_bytes * 8) / delta_time / 1_000_000
                        print(
                            f"[STATS] {label} outbound video: "
                            f"{mbps:.2f} Mbps, bytesSent={bytes_sent}, packetsSent={packets_sent}"
                        )
                else:
                    print(
                        f"[STATS] {label} outbound video initialized: "
                        f"bytesSent={bytes_sent}, packetsSent={packets_sent}"
                    )

                last_bytes = bytes_sent
                last_time = now


class LiveCameraTrack(VideoStreamTrack):
    def __init__(
        self,
        device_index=0,
        width=1920,
        height=1080,
        fps=30,
        preview=False,
        overlay=False,
    ):
        super().__init__()
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.preview = preview
        self.overlay = overlay

        self.cap = cv2.VideoCapture(device_index, capture_backend())

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open capture device index {device_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(
            f"Opened camera {device_index}: "
            f"{actual_w}x{actual_h} @ {actual_fps:.2f} fps"
        )

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ok, frame_bgr = self.cap.read()
        if not ok or frame_bgr is None:
            await asyncio.sleep(0.01)
            raise RuntimeError("Failed to read frame from capture device")

        if self.overlay:
            timestamp = time.strftime("%H:%M:%S")
            cv2.putText(
                frame_bgr,
                f"LIVE CAMERA {timestamp}",
                (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                3,
                cv2.LINE_AA,
            )

        if self.preview:
            cv2.imshow("WebRTC Source Preview", frame_bgr)
            cv2.waitKey(1)

        # Avoid explicit BGR -> RGB conversion.
        # PyAV accepts bgr24 directly.
        video_frame = VideoFrame.from_ndarray(frame_bgr, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.preview:
            cv2.destroyAllWindows()
        super().stop()


async def index(request):
    html = (HERE / "index.html").read_text()
    return web.Response(text=html, content_type="text/html")


async def health(request):
    return web.Response(text="server alive")


async def offer(request):
    print("Received /offer request")

    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    print("[SDP] Offer video codecs:")
    for codec in describe_video_codecs(offer.sdp):
        print(f"  - {codec}")

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state:", pc.connectionState)
        if pc.connectionState == "connected":
            asyncio.create_task(stats_loop(pc, label="webrtc"))
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            pcs.discard(pc)

    track = LiveCameraTrack(
        device_index=request.app["device_index"],
        width=request.app["width"],
        height=request.app["height"],
        fps=request.app["fps"],
        preview=request.app["preview"],
        overlay=request.app["overlay"],
    )

    sender = pc.addTrack(track)

    # Try sender parameter bitrate control.
    try:
        parameters = sender.getParameters()

        print(f"[PARAMS] Initial sender encodings: {parameters.encodings}")

        if parameters.encodings:
            parameters.encodings[0].maxBitrate = request.app["bitrate"]
            parameters.encodings[0].maxFramerate = request.app["fps"]

        await sender.setParameters(parameters)

        print(
            f"[PARAMS] Requested sender bitrate: "
            f"{request.app['bitrate'] / 1_000_000:.1f} Mbps, "
            f"fps: {request.app['fps']}"
        )

    except Exception as e:
        print(f"[PARAMS] Could not set sender parameters: {e}")

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()

    print("[SDP] Answer video codecs before forcing bitrate:")
    for codec in describe_video_codecs(answer.sdp):
        print(f"  - {codec}")

    await pc.setLocalDescription(answer)

    raw_answer_sdp = pc.localDescription.sdp

    print("[SDP] LocalDescription video codecs:")
    for codec in describe_video_codecs(raw_answer_sdp):
        print(f"  - {codec}")

    forced_sdp = force_video_bitrate_in_sdp(
        raw_answer_sdp,
        bitrate_bps=request.app["bitrate"],
    )

    print(
        f"[SDP] Added b=AS/b=TIAS video bitrate hints: "
        f"{request.app['bitrate'] / 1_000_000:.1f} Mbps"
    )

    return web.json_response(
        {
            "sdp": forced_sdp if request.app["force_sdp_bitrate"] else raw_answer_sdp,
            "type": pc.localDescription.type,
        }
    )


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    if coros:
        await asyncio.gather(*coros)
    pcs.clear()


def main():
    parser = argparse.ArgumentParser(
        description="Stream a Magewell USB Fusion SBS camera over WebRTC."
    )
    parser.add_argument("--device", type=int, default=0, help="Camera device index")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--bitrate",
        type=int,
        default=20_000_000,
        help="Target video bitrate in bits/sec",
    )
    parser.add_argument(
        "--force-sdp-bitrate",
        action="store_true",
        help="Inject b=AS/b=TIAS bitrate hints into answer SDP",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--preview", action="store_true", help="Show local OpenCV preview")
    parser.add_argument("--overlay", action="store_true", help="Draw timestamp overlay")
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List OpenCV capture devices and exit",
    )
    args = parser.parse_args()

    if args.list_devices:
        list_capture_devices()
        return

    app = web.Application()
    app["device_index"] = args.device
    app["width"] = args.width
    app["height"] = args.height
    app["fps"] = args.fps
    app["bitrate"] = args.bitrate
    app["preview"] = args.preview
    app["overlay"] = args.overlay
    app["force_sdp_bitrate"] = args.force_sdp_bitrate

    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)

    print("RUNNING LIVE CAMERA SERVER v5")
    print(f"Serving page at http://{args.host}:{args.port}/")
    print(f"Health check at http://{args.host}:{args.port}/health")
    print(f"Using device {args.device} at {args.width}x{args.height} {args.fps}fps")
    print(f"Requested bitrate: {args.bitrate / 1_000_000:.1f} Mbps")
    print(f"Force SDP bitrate: {args.force_sdp_bitrate}")
    print(f"Preview enabled: {args.preview}")
    print(f"Overlay enabled: {args.overlay}")

    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
