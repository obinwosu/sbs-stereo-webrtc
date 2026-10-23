# SBS Stereo WebRTC

Stream a da Vinci (or any dual-HDMI) stereo console into a custom Unity XR app.

USB Fusion composites the two eyes into one side-by-side UVC webcam. A Mac captures that webcam and serves a single WebRTC video track. Unity splits the texture per eye.

```
Console L/R DVI
      │
      ▼
Magewell USB Fusion  ──SBS mode──►  USB-C UVC webcam
      │
      ▼
Mac capture + aiortc server  ──/offer──►  Unity Quest app
      │
      ▼
StereoSBS shader: left half → left eye, right half → right eye
```

This is the v5 path that shipped in the Quest stereo viewer: one SBS track, not two peer connections.

## Repo layout

| Path | Role |
| --- | --- |
| `docs/hardware.md` | DVI-HDMI + Fusion wiring |
| `docs/fusion-api.md` | USB Fusion HTTP API used here |
| `docs/server.md` | WebRTC sender |
| `fusion/fusion_sbs.py` | Lock SBS and confirm both HDMI inputs |
| `server/` | OpenCV + aiortc capture server |
| `unity/` | Quest/Unity receiver scripts |

## Quick start

1. Wire the console into Fusion HDMI 1 and HDMI 2. Put the Fusion in **SBS**. Plug USB-C into the Mac. Details: [docs/hardware.md](docs/hardware.md).

2. Optional, if the Fusion is on the network:

   ```bash
   python fusion/fusion_sbs.py prepare --host 192.168.66.1 --password "$FUSION_PASSWORD"
   ```

3. On the Mac:

   ```bash
   cd server
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python webrtc_sbs_server.py --list-devices
   python webrtc_sbs_server.py --device 0 --width 1920 --height 1080 --fps 30
   ```

4. Confirm `http://<mac-lan-ip>:8080/` shows the SBS image in a browser.

5. In Unity, point `LiveStreamManager.offerUrl` at `http://<mac-lan-ip>:8080/offer` and use `Custom/StereoSBS` on the screen quad. See [unity/README.md](unity/README.md).

## Design choices

- **Composite on the Fusion.** Two DVI eyes become one UVC clock domain. That avoids dual-stream sync.
- **One WebRTC track.** The Quest app answers a single offer and writes one texture.
- **Split in the shader.** `unity_StereoEyeIndex` selects the half. Swap eyes with a material flag if the cables are reversed.
- **LAN HTTP signaling.** The client POSTs SDP to `/offer`. Quest builds need cleartext HTTP enabled.

## Hardware this was proven on

- da Vinci surgeon console stereo DVI outputs
- Magewell USB Fusion in SBS, USB-C into a Mac
- Custom Unity OpenXR app on Meta Quest (`com.ObiNwosu.queststereoviewer`)

Any two HDMI sources the Fusion can lock will work the same way.

## License

MIT. Magewell USB Fusion and da Vinci are trademarks of their owners. This repo does not include Magewell firmware or API PDFs.
