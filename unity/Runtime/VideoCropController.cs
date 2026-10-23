using UnityEngine;

public class VideoCropController : MonoBehaviour
{
    [SerializeField] private Renderer targetRenderer;

    [Header("Active video area inside the incoming texture")]
    [SerializeField] private int activeWidth = 1920;
    [SerializeField] private int activeHeight = 1080;

    private Material runtimeMat;

    void Start()
    {
        if (targetRenderer == null)
            targetRenderer = GetComponent<Renderer>();

        runtimeMat = targetRenderer.material;
    }

    void Update()
    {
        if (runtimeMat == null) return;

        Texture tex = runtimeMat.mainTexture;
        if (tex == null) return;
        if (tex.width <= 0 || tex.height <= 0) return;

        float cropScaleX = (float)activeWidth / tex.width;
        float cropScaleY = (float)activeHeight / tex.height;

        float cropOffsetX = (1f - cropScaleX) * 0.5f;
        float cropOffsetY = (1f - cropScaleY) * 0.5f;

        runtimeMat.SetVector("_CropScale", new Vector4(cropScaleX, cropScaleY, 0f, 0f));
        runtimeMat.SetVector("_CropOffset", new Vector4(cropOffsetX, cropOffsetY, 0f, 0f));
    }
}
