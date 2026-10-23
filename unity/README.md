# Unity stereo client

Drop-in scripts from the Quest app (`com.ObiNwosu.queststereoviewer`). They receive one SBS WebRTC track and split it per eye.

Tested with:

- Unity 6000.3
- `com.unity.webrtc` 3.0.0-pre.8
- Meta XR SDK / OpenXR on Quest

## Install

1. Copy `Runtime/*.cs` and `Runtime/*.shader` into `Assets/`.
2. Package Manager: add **WebRTC** (`com.unity.webrtc`).
3. Create a world-space quad (the stereo screen).
4. Make a material that uses `Custom/StereoSBS` and assign it to the quad.
5. Add `LiveStreamManager` to a GameObject.
6. Set **Target Renderer** to the quad.
7. Set **Offer Url** to `http://<mac-lan-ip>:8080/offer`.

## Eye split

`StereoSBS.shader` reads `unity_StereoEyeIndex`:

- left eye samples `uv.x * 0.5`
- right eye samples `0.5 + uv.x * 0.5`

If the console cables are swapped, set `_SwapEyes` to `1` on the material.

## Android / Quest HTTP

Quest blocks cleartext HTTP unless you allow it. Copy `Android/network_security_config.xml` to `Assets/Plugins/Android/` and add these attributes on `<application>`:

```xml
android:usesCleartextTraffic="true"
android:networkSecurityConfig="@xml/network_security_config"
```

See `Android/AndroidManifest.snippet.xml`.

The Quest and the Mac must be on the same LAN. The headset must be able to open `http://<mac-lan-ip>:8080/health`.

## Optional scripts

- `VideoCropController` — if the decoded texture is larger than the active 1920x1080 picture, set crop uniforms. The stock `StereoSBS` shader does not consume those uniforms unless you extend it.
- `ScreenResizeHandle` — grab the quad corner with the right Trigger. Requires Meta `OVRInput`.
- `MonoShader` — show the full SBS frame in one eye for debugging.

## Scene checklist

- [ ] Quad uses `Custom/StereoSBS`
- [ ] `LiveStreamManager.offerUrl` is the Mac LAN address, not `localhost`
- [ ] Cleartext HTTP is allowed in the Android manifest
- [ ] Headset Wi-Fi can reach port 8080
- [ ] Server is running before the scene starts (the client offers once on `Start`)
