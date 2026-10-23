# USB Fusion API notes

The helper in `fusion/fusion_sbs.py` talks to the Magewell USB Fusion HTTP API so you can confirm HDMI lock and switch to SBS without walking to the box.

Source: *USB Fusion API* (firmware 2.4.68 and above). V2.0 paths below are for firmware 2.6.0+.

## Reachability

The Fusion Web UI and API listen on the device IPv4 address.

- Factory AP address: `http://192.168.66.1`
- Ethernet / USB NET: use the address shown in the Web UI

Most calls need a login cookie. Passwords are SHA-256 hex, not plaintext.

```http
POST /api/user/login
{"username":"Admin","password":"<sha256 hex>"}
```

The session cookie looks like `sid-<serial>=<sid>`.

## Calls used here

| Action | Path | Body |
| --- | --- | --- |
| Ping | `POST /api/ping` | none |
| Login | `POST /api/user/login` | `username`, SHA-256 `password` |
| Stay awake | `POST /mwapi/V2.0/general/block-goto-sleep` | `{"block":1}` |
| Dashboard | `POST /mwapi/V2.0/dashboard/get-summary-info` | none |
| USB-C output | `POST /mwapi/V2.0/output/get-usb-output-config` | none |
| Scene list | `POST /mwapi/V2.0/scene/get-scenes-list` | none |
| Switch scene | `POST /mwapi/V2.0/scene/switch-scene` | `{"sceneId": N}` |
| Press SBS | `GET /mwapi/V2.0/button/action/5` | none |

HDMI signal `status` values:

- `0` no signal
- `1` unsupported
- `2` locking
- `3` locked / capturable

Scene `template` values:

- `0` picture-in-picture
- `1` side-by-side
- `2` single source

`prepare` prefers a saved scene with `template == 1`. If none exists, it presses button 5 (SBS).

## Helper

```bash
export FUSION_PASSWORD='your-password'
python fusion/fusion_sbs.py prepare --host 192.168.66.1
```

Other commands: `ping`, `status`, `sbs`.

Do not commit Fusion passwords. Use `FUSION_PASSWORD` or `--password`.
