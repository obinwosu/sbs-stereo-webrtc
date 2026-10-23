# Unity SBS stereo client

Drop-in scripts from the Quest app `com.ObiNwosu.queststereoviewer`.
They receive one WebRTC video track and split it per eye.

Tested with:

- Unity 6000.3
- `com.unity.webrtc` 3.0.0-pre.8
- Meta XR SDK / OpenXR on Quest 3

## Scene wiring

1. Install `com.unity.webrtc`.
2. Copy `Runtime/` into `Assets`.
3. Create a world-space quad in front of the XR camera.
4. Assign `StereoSBS.shader` to that quad's material.
5. Add `LiveStreamManager` to an empty object.
6. Set `targetRenderer` to the quad.
7. Set `offerUrl` to `http://<mac-lan-ip>:8080/offer`.

`LiveStreamManager` creates a recv-only video transceiver, POSTs the SDP
offer, and writes incoming frames onto `_MainTex`.

`StereoSBS.shader` uses `unity_StereoEyeIndex`:

- left eye samples the left half
- right eye samples the right half
- `_SwapEyes` flips that if the Fusion inputs are reversed

Optional:

- `VideoCropController` if the capture texture is letterboxed
- `ScreenResizeHandle` to grab-scale the in-world screen on Quest
- `MonoShader` for 2D preview without stereo split

## Android / Quest HTTP

Quest builds block cleartext HTTP unless you allow it. Copy
`Android/network_security_config.xml` to `Assets/Plugins/Android/` and add
the attributes in `Android/AndroidManifest.snippet.xml` to the
`<application>` element.

The Quest and the Mac must be on the same LAN. Update `offerUrl` before
each build if the Mac DHCP address changed.
