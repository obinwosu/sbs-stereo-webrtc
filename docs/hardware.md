# Hardware setup

This is the capture path that worked for a da Vinci surgeon console into a Quest Unity app.

## Signal path

```
da Vinci console left DVI  --DVI-HDMI-->  Fusion HDMI 1
da Vinci console right DVI --DVI-HDMI-->  Fusion HDMI 2
USB Fusion SBS layout      --USB-C UVC--> Mac webcam
Mac WebRTC server          --LAN------->  Unity / Quest
```

The Fusion, not the Mac, does the stereo composite. The Mac sees one 1080p side-by-side webcam.

## What you need

- da Vinci surgeon console with two DVI video outputs (left eye, right eye)
- Two DVI-to-HDMI cables
- [Magewell USB Fusion](https://www.magewell.com/capture/usb-fusion)
- USB-C cable from Fusion USB OUT to the Mac (use the supplied USB 3.0 cable)
- Fusion power adapter (the unit must be powered; bus power is not enough)
- Mac on the same LAN as the headset
- Quest or other OpenXR headset for the Unity client

USB Fusion inputs are HDMI 1.4, up to 1080p60. That matches typical console DVI output after a DVI-HDMI adapter.

## Fusion layout

1. Power the Fusion.
2. Connect left-eye DVI-HDMI to **HDMI 1**.
3. Connect right-eye DVI-HDMI to **HDMI 2**.
4. Press the **SBS** button until HDMI 1 and HDMI 2 are the two panes.
5. Long-press SBS if you need a 50/50 split. A divider that is not centered will warp stereo.
6. Connect **USB OUT** (Type-C) to the Mac. The Fusion appears as a driver-free UVC webcam.
7. Optional: use the Fusion HDMI OUT monitor to confirm both eyes before you start the server.

Front-panel buttons, from the USB Fusion quick start guide:

| Button | Short press | Long press |
| --- | --- | --- |
| 1 | HDMI 1 only | |
| 2 | HDMI 2 only | Screencast |
| 3 | USB webcam | |
| 4 | Picture-in-picture | Move PIP window |
| 5 | Side-by-side | Change SBS ratio |

Do not leave the unit in PIP mode. The Unity shader expects a 50/50 SBS frame.

## Why one SBS track

Sending two independent WebRTC videos makes left/right sync harder. USB Fusion already locks both HDMI inputs to one UVC clock. Unity then samples the left half for the left eye and the right half for the right eye.

## Checks before streaming

- Both HDMI LEDs are on.
- Fusion Web UI or `fusion/fusion_sbs.py status` shows HDMI 1 and HDMI 2 as **locked**.
- USB link is USB 3 (`super-speed-5g`). USB 2 will drop frames at 1080p.
- Preview on the Mac shows left | right, not a single eye or PIP.

If one half is black, the matching DVI-HDMI cable or console output is dark. If both halves show the same eye, the Fusion is not in HDMI1+HDMI2 SBS.
