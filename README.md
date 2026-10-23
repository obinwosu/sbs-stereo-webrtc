# SBS Stereo WebRTC

Stream a da Vinci (or any dual-HDMI) stereo console into a custom Unity XR app.

The capture box composites left and right into **one side-by-side frame**.
WebRTC sends that single track. Unity splits the halves per eye at display time.

```
da Vinci left/right
        |  two DVI-HDMI cables
        v
Magewell USB Fusion  (SBS 50/50)
        |  USB-C UVC
        v
Mac OpenCV + aiortc server
        |  WebRTC  /offer
        v
Unity Quest app  (StereoSBS shader)
```

This is the working v5 path: Magewell USB Fusion SBS mode, USB-C into a Mac,
Python WebRTC sender, Unity `com.unity.webrtc` receiver.

## Why one track

The Fusion already makes the stereo pair. Sending two peer connections would
add sync and signaling complexity without a quality win. The Unity shader
samples:

- left eye: `uv.x * 0.5`
- right eye: `0.5 + uv.x * 0.5`

## Quick start

### 1. Hardware

See [docs/hardware.md](docs/hardware.md).

1. Left console eye → Fusion HDMI 1
2. Right console eye → Fusion HDMI 2
3. Fusion USB-C → Mac
4. Short-press **SBS** until the layout is HDMI 1 | HDMI 2, 50/50

Optional, if the Fusion is on the network:

```bash
export FUSION_PASSWORD='your-password'
python fusion/fusion_sbs.py --host 192.168.66.1 prepare
```

### 2. Server

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python webrtc_sbs_server.py --list-devices
python webrtc_sbs_server.py --device 0 --width 1920 --height 1080 --fps 30 --bitrate 20000000 --preview
```

Open `http://<mac-ip>:8080/` on the Mac to confirm the SBS image.

### 3. Unity client

See [unity/README.md](unity/README.md). Point `LiveStreamManager.offerUrl` at
`http://<mac-ip>:8080/offer`, assign `StereoSBS` to the screen quad, build to
Quest.

## Repo layout

| Path | Role |
| --- | --- |
| `server/` | aiortc camera sender + browser tester |
| `fusion/` | USB Fusion HTTP helper for SBS / HDMI status |
| `unity/` | WebRTC receiver, stereo shader, Quest HTTP config |
| `docs/` | Hardware map and Fusion API notes |

## Design notes

- Default capture is 1920x1080 at 30 fps, 20 Mbps. That matches Fusion HDMI 1.4 inputs.
- `--force-sdp-bitrate` injects `b=AS` / `b=TIAS` when `setParameters` is ignored.
- The Quest app must allow cleartext HTTP to reach a LAN signaling server.
- Eyes are not two cameras on the Mac. If stereo looks wrong, fix Fusion layout or `_SwapEyes`, not the server.

## License

MIT. Magewell USB Fusion is a third-party product; its API and manuals remain Magewell's.
