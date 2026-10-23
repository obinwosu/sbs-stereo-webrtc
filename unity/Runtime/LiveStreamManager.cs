using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Unity.WebRTC;

[Serializable]
public class SdpMessage
{
    public string sdp;
    public string type;
}

public class LiveStreamManager : MonoBehaviour
{
    [Header("Scene References")]
    public Renderer targetRenderer;

    [Header("Signaling")]
    public string offerUrl = "http://10.246.130.11:8080/offer"; // Mac LAN IP running server/webrtc_sbs_server.py

    private RTCPeerConnection pc;
    private VideoStreamTrack remoteVideoTrack;
    private Coroutine webRtcUpdateCoroutine;

    private void Start()
    {
        Debug.Log("[WebRTC] LiveStreamManager Start called");
        Debug.Log("[WebRTC] offerUrl in use = " + offerUrl);

        if (targetRenderer == null)
        {
            Debug.LogError("[WebRTC] targetRenderer is NULL");
            return;
        }

        StartCoroutine(StartReceiver());
    }

    private IEnumerator StartReceiver()
    {
        Debug.Log("[WebRTC] StartReceiver entered");

        var config = new RTCConfiguration
        {
            iceServers = new RTCIceServer[]
            {
                new RTCIceServer
                {
                    urls = new string[] { "stun:stun.l.google.com:19302" }
                }
            }
        };

        Debug.Log("[WebRTC] Creating peer connection");
        pc = new RTCPeerConnection(ref config);

        pc.OnConnectionStateChange = state =>
        {
            Debug.Log("[WebRTC] Connection state: " + state);
        };

        pc.OnIceConnectionChange = state =>
        {
            Debug.Log("[WebRTC] ICE connection state: " + state);
        };

        pc.OnTrack = e =>
        {
            Debug.Log("[WebRTC] OnTrack fired: " + e.Track.Kind);

            if (e.Track is VideoStreamTrack videoTrack)
            {
                remoteVideoTrack = videoTrack;

                remoteVideoTrack.OnVideoReceived += texture =>
                {
                    Debug.Log("[WebRTC] Video frame received: " + texture.width + "x" + texture.height);

                    if (targetRenderer != null)
                    {
                        targetRenderer.material.SetTexture("_MainTex", texture);
                    }
                    else
                    {
                        Debug.LogError("[WebRTC] targetRenderer became NULL");
                    }
                };
            }
        };

        Debug.Log("[WebRTC] Adding video transceiver");
        pc.AddTransceiver(TrackKind.Video);

        Debug.Log("[WebRTC] Starting WebRTC.Update coroutine");
        webRtcUpdateCoroutine = StartCoroutine(WebRTC.Update());

        Debug.Log("[WebRTC] Creating offer");
        var offerOp = pc.CreateOffer();
        yield return offerOp;

        if (offerOp.IsError)
        {
            Debug.LogError("[WebRTC] CreateOffer error: " + offerOp.Error.message);
            yield break;
        }

        var offerDesc = offerOp.Desc;
        Debug.Log("[WebRTC] Offer created");

        Debug.Log("[WebRTC] Setting local description");
        var setLocalOp = pc.SetLocalDescription(ref offerDesc);
        yield return setLocalOp;

        if (setLocalOp.IsError)
        {
            Debug.LogError("[WebRTC] SetLocalDescription error: " + setLocalOp.Error.message);
            yield break;
        }

        Debug.Log("[WebRTC] Local description set");

        var localDesc = pc.LocalDescription;

        var offerMsg = new SdpMessage
        {
            sdp = localDesc.sdp,
            type = "offer"
        };

        string json = JsonUtility.ToJson(offerMsg);
        byte[] bodyRaw = Encoding.UTF8.GetBytes(json);

        Debug.Log("[WebRTC] Sending offer to " + offerUrl);

        using (var req = new UnityWebRequest(offerUrl, "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(bodyRaw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            yield return req.SendWebRequest();

#if UNITY_2020_2_OR_NEWER
            if (req.result != UnityWebRequest.Result.Success)
#else
            if (req.isNetworkError || req.isHttpError)
#endif
            {
                Debug.LogError("[WebRTC] Offer POST failed: " + req.error);
                Debug.LogError("[WebRTC] Response code: " + req.responseCode);
                Debug.LogError("[WebRTC] Response text: " + req.downloadHandler.text);
                yield break;
            }

            Debug.Log("[WebRTC] Offer POST succeeded");
            Debug.Log("[WebRTC] Raw answer text: " + req.downloadHandler.text);

            var answerMsg = JsonUtility.FromJson<SdpMessage>(req.downloadHandler.text);

            if (answerMsg == null || string.IsNullOrEmpty(answerMsg.sdp))
            {
                Debug.LogError("[WebRTC] Answer JSON was empty or invalid");
                yield break;
            }

            var answerDesc = new RTCSessionDescription
            {
                type = RTCSdpType.Answer,
                sdp = answerMsg.sdp
            };

            Debug.Log("[WebRTC] Applying remote answer");
            var setRemoteOp = pc.SetRemoteDescription(ref answerDesc);
            yield return setRemoteOp;

            if (setRemoteOp.IsError)
            {
                Debug.LogError("[WebRTC] SetRemoteDescription error: " + setRemoteOp.Error.message);
                yield break;
            }

            Debug.Log("[WebRTC] Remote answer applied successfully");
        }
    }

    private void OnDestroy()
    {
        Debug.Log("[WebRTC] LiveStreamManager OnDestroy");

        if (webRtcUpdateCoroutine != null)
        {
            StopCoroutine(webRtcUpdateCoroutine);
            webRtcUpdateCoroutine = null;
        }

        if (remoteVideoTrack != null)
        {
            remoteVideoTrack.Dispose();
            remoteVideoTrack = null;
        }

        if (pc != null)
        {
            pc.Close();
            pc.Dispose();
            pc = null;
        }
    }
}