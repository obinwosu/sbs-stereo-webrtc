using UnityEngine;

public class ScreenResizeHandle : MonoBehaviour
{
    [Header("References")]
    public Transform screenQuad;
    public Transform rightController;

    [Header("Resize Settings")]
    public float minWidth = 0.8f;
    public float maxWidth = 4.5f;
    public float aspectRatio = 16f / 9f;
    public float grabDistance = 0.12f;

    private bool isDragging = false;

    void Update()
    {
        if (screenQuad == null || rightController == null) return;

        float distance = Vector3.Distance(rightController.position, transform.position);
        bool closeEnough = distance <= grabDistance;

        if (!isDragging && closeEnough && OVRInput.GetDown(OVRInput.Button.SecondaryIndexTrigger))
        {
            isDragging = true;
        }

        if (isDragging && OVRInput.GetUp(OVRInput.Button.SecondaryIndexTrigger))
        {
            isDragging = false;
        }

        if (isDragging)
        {
            ResizeFromController();
        }
    }

    void ResizeFromController()
    {
        Vector3 localPoint = screenQuad.InverseTransformPoint(rightController.position);

        float width = Mathf.Abs(localPoint.x) * 2f;
        width = Mathf.Clamp(width, minWidth, maxWidth);

        float height = width / aspectRatio;

        screenQuad.localScale = new Vector3(width, height, 1f);

        UpdateHandlePosition();
    }

    void UpdateHandlePosition()
    {
        float zOffset = transform.localPosition.z;
        transform.localPosition = new Vector3(0.5f, -0.5f, zOffset);
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, grabDistance);
    }
}