# Magewell USB Fusion API notes

These are the endpoints this repo uses from the official USB Fusion API
(firmware 2.4.68+, V2.0 paths for 2.6.0+). The full vendor PDF is not
redistributed here.

## How to talk to the device

- HTTP + JSON
- Default AP address: `http://192.168.66.1`
- Login: `POST /api/user/login`
- Password is sent as SHA-256 hex, not plaintext
- Session cookie looks like `sid-<serial>=<sid>`
- Most control calls: `POST /mwapi/V2.0/<group>/<action>`
- Older firmware: drop `V2.0` and use `/mwapi/<action>`

```bash
export FUSION_PASSWORD='your-password'
python fusion/fusion_sbs.py ping
python fusion/fusion_sbs.py status
python fusion/fusion_sbs.py prepare
```

`prepare` logs in, blocks sleep, checks HDMI 1/2, then switches to a saved
SBS scene (`template == 1`) or presses front-panel button 5.

## Endpoints used here

| Action | Path |
| --- | --- |
| Ping | `/api/ping` |
| Login | `/api/user/login` |
| Device + I/O summary | `/mwapi/V2.0/dashboard/get-summary-info` |
| Block sleep | `/mwapi/V2.0/general/block-goto-sleep` |
| HDMI signal | `/mwapi/V2.0/input/get-signal-info` (`source-id` 0 or 1) |
| USB-C / UVC config | `/mwapi/V2.0/output/get-usb-output-config` |
| Scene list | `/mwapi/V2.0/scene/get-scenes-list` |
| Switch scene | `/mwapi/V2.0/scene/switch-scene` |
| Press button | `/mwapi/V2.0/button/action/n` |

## Values that matter for stereo

HDMI / webcam signal `status`:

- `0` no signal
- `1` unsupported
- `2` locking
- `3` locked / capturable

Scene `template`:

- `0` picture-in-picture
- `1` side-by-side
- `2` single source

Front-panel buttons, left to right:

1. HDMI 1
2. HDMI 2
3. WEB CAMERA 3
4. PIP
5. SBS

`USBOutData.speed` should be `super-speed-5g` when the Mac is on USB 3.
`uvc-running` becomes true once the WebRTC server opens the camera.

A 50/50 SBS split is a vertical `dividerLine` at `x1 = x2 = 500000`
(relative 0–1 scaled by 1,000,000).

## Sources

- [USB Fusion product page](https://www.magewell.com/capture/usb-fusion)
- USB Fusion API document (`usb-fusion-api-en_US.pdf`)
- USB Fusion user manual
