// Unity 6000.6.2f1. Copy outside Assets/Editor; AnimationStudy adds/configures this preview component.
// Constant-speed inspection on a flat floor, not player input, navigation or collision handling.
using UnityEngine;

public sealed class StudyLocomotion : MonoBehaviour
{
    [Min(0)] public float speed;
    [Min(.01f)] public float duration = 1;
    public Camera previewCamera;
    Vector3 start;
    Vector3 cameraOffset;
    double elapsed;

    void Start()
    {
        if (duration <= 0 || speed < 0 || previewCamera == null)
        {
            Debug.LogError("StudyLocomotion requires a camera, positive duration and nonnegative speed.", this);
            enabled = false;
            return;
        }
        start = transform.position;
        cameraOffset = previewCamera.transform.position-start;
    }

    void Update()
    {
        elapsed += Time.deltaTime;
        float time = (float)(elapsed % (duration*4));
        transform.position = start + transform.forward*speed*time;
    }

    void LateUpdate()
    {
        previewCamera.transform.position = transform.position + cameraOffset;
    }
}
