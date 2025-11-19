using UnityEngine;
using UnityEngine.XR;
using System.Net;
using System.Net.Sockets;
using System.Text;

public class VRCarController : MonoBehaviour
{
    [Header("네트워크 설정")]
    public string raspberryPiIP = "192.168.45.246"; // 라즈베리파이 IP
    public int port = 5005;

    [Header("VR 입력")]
    public XRNode controllerNode = XRNode.RightHand; // 오른손 컨트롤러

    private UdpClient udpClient;
    private InputDevice controller;
    private string lastCommand = "S";

    void Start()
    {
        // UDP 클라이언트 초기화
        udpClient = new UdpClient();
        Debug.Log($"UDP 클라이언트 준비: {raspberryPiIP}:{port}");

        // VR 컨트롤러 찾기
        controller = InputDevices.GetDeviceAtXRNode(controllerNode);
    }

    void Update()
    {
        // 컨트롤러가 연결되지 않았으면 다시 찾기
        if (!controller.isValid)
        {
            controller = InputDevices.GetDeviceAtXRNode(controllerNode);
            return;
        }

        string command = GetControllerCommand();

        // 명령이 바뀌었을 때만 전송
        if (command != lastCommand)
        {
            SendCommand(command);
            lastCommand = command;
        }
    }

    string GetControllerCommand()
    {
        // 조이스틱 입력 받기
        Vector2 joystick;
        if (controller.TryGetFeatureValue(CommonUsages.primary2DAxis, out joystick))
        {
            // 조이스틱 방향에 따라 명령 결정
            if (joystick.y > 0.5f)
                return "F"; // 위: 전진
            else if (joystick.y < -0.5f)
                return "B"; // 아래: 후진
            else if (joystick.x < -0.5f)
                return "L"; // 왼쪽: 좌회전
            else if (joystick.x > 0.5f)
                return "R"; // 오른쪽: 우회전
        }

        return "S"; // 조이스틱 중립: 정지
    }

    void SendCommand(string command)
    {
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(command);
            udpClient.Send(data, data.Length, raspberryPiIP, port);
            Debug.Log($"명령 전송: {command}");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"전송 실패: {e.Message}");
        }
    }

    void OnDestroy()
    {
        // 종료 시 정지 명령 전송
        SendCommand("S");
        udpClient?.Close();
    }
}
