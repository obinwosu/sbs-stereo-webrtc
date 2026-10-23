# WebRTC capture server

`server/webrtc_sbs_server.py` is the v5 live-camera sender. It opens the Fusion UVC device with OpenCV and answers WebRTC offers with one video track.

## Install

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, OpenCV uses AVFoundation so the Fusion shows up as a normal webcam.

## Find the Fusion camera

```bash
python list_cameras.py
# or
python webrtc_sbs_server.py --list-devices
```

Look for a 1920x1080 device that actually returns frames.

## Run

```bash
python webrtc_sbs_server.py \
  --device 0 \
  --width 1920 \
  --height 1080 \
  --fps 30 \
  --bitrate 20000000 \
  --host 0.0.0.0 \
  --port 8080
```

Useful flags:

- `--preview` local OpenCV window of the SBS frame
- `--overlay` timestamp (debug only; do not leave this on for stereo)
- `--force-sdp-bitrate` inject `b=AS` / `b=TIAS` if `setParameters` is ignored

## Signaling

The Unity client creates the offer. The server answers.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Browser test page |
| GET | `/health` | Liveness |
| POST | `/offer` | SDP offer in, SDP answer out |

JSON body:

```json
{"sdp": "...", "type": "offer"}
```

Point the headset at `http://<mac-lan-ip>:8080/offer`. First confirm the same URL in a laptop browser on the same Wi-Fi.

## Capture settings

Match `--width` / `--height` / `--fps` to the Fusion USB output. For a 50/50 SBS composite of two 1080p eyes, 1920x1080 at 30 fps and 20 Mbps is the combination that was used in the Quest app.

If OpenCV reports a different size than you requested, use the actual size in Unity or crop with `VideoCropController`.
