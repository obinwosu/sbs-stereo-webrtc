# Hardware setup

This path was used with a da Vinci surgeon console and a Magewell USB Fusion.

## What you need

- da Vinci console stereo outputs (two DVI ports: left eye and right eye)
- Two DVI-to-HDMI cables
- [Magewell USB Fusion](https://www.magewell.com/capture/usb-fusion)
- USB-C cable from Fusion to the Mac (use the supplied USB 3.0 cable)
- Fusion power supply
- Mac on the same LAN as the Quest / Unity client

## Cable map

```
da Vinci left eye  --DVI-HDMI--> Fusion HDMI 1
da Vinci right eye --DVI-HDMI--> Fusion HDMI 2
Fusion USB-C OUT   --USB 3.0---> Mac
Fusion HDMI OUT                  optional monitor preview
```

Keep left on HDMI 1 and right on HDMI 2. If they are reversed, swap the cables or set `_SwapEyes` on the Unity `StereoSBS` material.

## Fusion layout

1. Power the Fusion and wait until it boots.
2. Confirm HDMI 1 and HDMI 2 LEDs are lit.
3. Short-press the **SBS** button until the layout is HDMI 1 | HDMI 2.
4. Long-press **SBS** until the split is 50/50 (`dividerLine` at x = 0.5).
5. Connect USB-C to the Mac. The Fusion appears as a driver-free UVC webcam.

The Fusion composites both eyes into one 1920x1080 program frame. That is what OpenCV and WebRTC capture. Do not try to open HDMI 1 and HDMI 2 as two cameras on the Mac.

USB Fusion HDMI inputs are HDMI 1.4, up to about 1080p60. Match the console output to that.

## Mac capture

On the Mac the Fusion shows up as a normal camera. Find its OpenCV index:

```bash
python server/webrtc_sbs_server.py --list-devices
```

Then start the server with that `--device` and a size that matches the Fusion USB output, usually `1920x1080`.

Use a USB 3.0 port. If the Fusion reports `high-speed` instead of `super-speed-5g`, the Mac is on USB 2.0 and the stream will struggle.

## Network

The WebRTC server binds `0.0.0.0:8080` by default. The Quest app POSTs an SDP offer to `http://<mac-lan-ip>:8080/offer`. Both devices need to reach each other on that LAN. Phone-hotspot or isolated OR networks often block this.

## Optional Fusion control

The Fusion also has a Web UI / HTTP API (default AP `192.168.66.1`). Use `fusion/fusion_sbs.py` to confirm both HDMI inputs are locked, keep the unit awake, and switch to SBS without touching the front panel. See [fusion-api.md](fusion-api.md).
