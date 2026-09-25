// Unity 6000.6.2f1. Put outside Assets/Editor.
// Requires a baked/registered NavMesh, a NavMeshAgent, and an in-place Generic Animator
// with float parameters "MoveBlend" and "WalkRate" (authored walk speed: 0.72 m/s).
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(NavMeshAgent))]
public sealed class ClickToMove : MonoBehaviour
{
    public Camera inputCamera;
    public Animator animator;
    public LayerMask clickMask;
    public int floorLayer = 8;
    public float authoredWalkSpeed = .72f;
    public LineRenderer route;
    public Transform targetMarker;
    public Rect blockedScreenRect;
    public bool acceptPointerInput = true;

    public string Status { get; private set; } = "Click the floor to move.";
    public Vector3 Destination { get; private set; }
    public bool HasDestination { get; private set; }
    public int AcceptedCommands { get; private set; }
    public int RejectedCommands { get; private set; }
    public float MoveBlend => animator.GetFloat(BlendId);
    public NavMeshAgent Agent { get; private set; }
    static readonly int BlendId = Animator.StringToHash("MoveBlend");
    static readonly int RateId = Animator.StringToHash("WalkRate");
    Vector3 spawn;
    Quaternion spawnRotation;
    NavMeshPath path;

    void Start()
    {
        Agent = GetComponent<NavMeshAgent>();
        path = new NavMeshPath();
        if (inputCamera == null || animator == null || authoredWalkSpeed <= 0 || !Agent.isOnNavMesh)
        {
            Status = "Navigation setup failed; see the player log.";
            Debug.LogError("ClickToMove needs a camera, animator, positive clip speed and an agent on a NavMesh.", this);
            enabled = false;
            return;
        }
        spawn = transform.position;
        spawnRotation = transform.rotation;
        Agent.updateRotation = false;
        animator.applyRootMotion = false;
        animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        if (targetMarker != null) targetMarker.gameObject.SetActive(false);
        if (route != null) route.positionCount = 0;
    }

    public bool TryMoveFromScreen(Vector2 screenPosition)
    {
        // GUI coordinates are top-left based; pointer coordinates are bottom-left based.
        if (blockedScreenRect.Contains(new Vector2(screenPosition.x, Screen.height-screenPosition.y)))
            return Reject("Choose a destination on the floor, below the controls.");
        if (screenPosition.x < 0 || screenPosition.y < 0 ||
            screenPosition.x >= Screen.width || screenPosition.y >= Screen.height)
            return Reject("That point is outside the view.");
        if (!Physics.Raycast(inputCamera.ScreenPointToRay(screenPosition), out var hit, 100,
            clickMask, QueryTriggerInteraction.Ignore))
            return Reject("Click the diorama floor.");
        if (hit.collider.gameObject.layer != floorLayer)
            return Reject("That is an obstacle. Choose clear floor.");
        return TryMoveTo(hit.point);
    }

    public bool TryMoveTo(Vector3 point)
    {
        if (Agent == null || !Agent.enabled || !Agent.isOnNavMesh)
            return Reject("The character is not on a walkable surface.");
        if (!NavMesh.SamplePosition(point, out var hit, .08f, Agent.areaMask) ||
            Mathf.Abs(hit.position.y-point.y) > .08f)
            return Reject("There is not enough walking clearance at that point.");
        if (!Agent.CalculatePath(hit.position, path) || path.status != NavMeshPathStatus.PathComplete)
            return Reject("That destination is unreachable.");
        if (!Agent.SetPath(path))
            return Reject("The navigation path could not be applied.");
        Agent.isStopped = false;
        Destination = hit.position;
        HasDestination = true;
        AcceptedCommands++;
        Status = "Walking to your destination.";
        if (targetMarker != null)
        {
            targetMarker.position = Destination + Vector3.up*.025f;
            targetMarker.gameObject.SetActive(true);
        }
        DrawRoute();
        return true;
    }

    bool Reject(string message)
    {
        Status = message;
        RejectedCommands++;
        return false;
    }

    public void Stop()
    {
        if (Agent == null || !Agent.isOnNavMesh) return;
        Agent.isStopped = true;
        Agent.velocity = Vector3.zero;
        Agent.ResetPath();
        HasDestination = false;
        Status = "Stopped. Click the floor to choose a new destination.";
        if (route != null) route.positionCount = 0;
        if (targetMarker != null) targetMarker.gameObject.SetActive(false);
    }

    public void ResetToSpawn()
    {
        Stop();
        if (Agent == null || !Agent.Warp(spawn))
        {
            Status = "Could not return to the starting point.";
            Debug.LogError(Status, this);
            return;
        }
        transform.rotation = spawnRotation;
        animator.SetFloat(BlendId, 0);
        animator.SetFloat(RateId, 1);
        Status = "Back at the start. Click the floor to move.";
    }

    void DrawRoute()
    {
        if (route == null) return;
        var corners = Agent.path.corners;
        route.positionCount = corners.Length;
        for (int i = 0; i < corners.Length; i++) route.SetPosition(i, corners[i]+Vector3.up*.018f);
    }

    void Update()
    {
        if (acceptPointerInput)
        {
            if (Input.GetMouseButtonDown(0)) TryMoveFromScreen(Input.mousePosition);
            if (Input.GetMouseButtonDown(1) || Input.GetKeyDown(KeyCode.Space)) Stop();
            if (Input.GetKeyDown(KeyCode.R)) ResetToSpawn();
            if (Input.GetKeyDown(KeyCode.Escape)) Application.Quit();
        }
        float speed = Agent.velocity.magnitude;
        float blend = Mathf.Clamp01(speed/authoredWalkSpeed);
        animator.SetFloat(BlendId, blend);
        // Keep an abrupt stop's outgoing-state clock running through its crossfade.
        animator.SetFloat(RateId, speed > .015f ? Mathf.Max(.15f, speed/authoredWalkSpeed) : 1);
        if (speed > .015f)
            transform.rotation = Quaternion.RotateTowards(transform.rotation,
                Quaternion.LookRotation(Agent.velocity), Agent.angularSpeed*Time.deltaTime);
        if (HasDestination && !Agent.pathPending && Agent.remainingDistance <= Agent.stoppingDistance+.015f &&
            speed < .035f)
        {
            Agent.ResetPath();
            HasDestination = false;
            Status = "Arrived. Choose your next destination.";
            if (targetMarker != null) targetMarker.gameObject.SetActive(false);
        }
        if (HasDestination) DrawRoute();
        else if (route != null) route.positionCount = 0;
    }
}
