using System;
using System.Collections;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class MJPEGStreamPlayer : MonoBehaviour
{
    [Header("Stream Settings")]
    public string streamHost = "raspberrypi.local";
    public int streamPort = 8080;
    public string streamPath = "/?action=stream";
    
    [Header("Display")]
    public Renderer targetRenderer;
    
    [Header("Status")]
    public bool isConnected = false;
    public int framesReceived = 0;
    
    private Texture2D texture;
    private bool isStreaming = false;
    private Thread streamThread;
    
    void Start()
    {
        // Main Thread Dispatcher 초기화
        UnityMainThreadDispatcher.Instance();
        
        // 스트리밍 시작
        StartStreaming();
    }
    
    public void StartStreaming()
    {
        if (isStreaming) return;
        
        isStreaming = true;
        streamThread = new Thread(StreamWorker);
        streamThread.IsBackground = true;
        streamThread.Start();
        
        Debug.Log($"📡 MJPEG 스트림 시작: {streamHost}:{streamPort}{streamPath}");
    }
    
    public void StopStreaming()
    {
        isStreaming = false;
        if (streamThread != null && streamThread.IsAlive)
        {
            streamThread.Join(1000);
        }
        Debug.Log("🛑 스트림 중지");
    }
    
    void StreamWorker()
    {
        while (isStreaming)
        {
            TcpClient tcpClient = null;
            NetworkStream stream = null;
            
            try
            {
                // TCP 연결
                tcpClient = new TcpClient();
                tcpClient.ReceiveBufferSize = 1024 * 1024; // 1MB 버퍼
                tcpClient.Connect(streamHost, streamPort);
                stream = tcpClient.GetStream();
                
                // HTTP GET 요청
                string request = $"GET {streamPath} HTTP/1.1\r\n" +
                                $"Host: {streamHost}\r\n" +
                                "Connection: keep-alive\r\n\r\n";
                byte[] requestBytes = Encoding.ASCII.GetBytes(request);
                stream.Write(requestBytes, 0, requestBytes.Length);
                
                Debug.Log("✅ MJPEG 스트림 연결 성공!");
                isConnected = true;
                
                // HTTP 헤더 건너뛰기
                using (StreamReader reader = new StreamReader(stream, Encoding.ASCII, false, 1024, true))
                {
                    string line;
                    while ((line = reader.ReadLine()) != null && line != "") { }
                }
                
                // MJPEG 프레임 읽기
                byte[] buffer = new byte[1024 * 1024]; // 1MB
                int bufferPos = 0;
                
                while (isStreaming && tcpClient.Connected)
                {
                    int bytesRead = stream.Read(buffer, bufferPos, buffer.Length - bufferPos);
                    if (bytesRead <= 0)
                    {
                        Debug.LogWarning("⚠️ 스트림 끊김");
                        break;
                    }
                    
                    bufferPos += bytesRead;
                    
                    // JPEG 시작 (0xFF 0xD8)과 끝 (0xFF 0xD9) 찾기
                    int jpegStart = FindBytes(buffer, bufferPos, new byte[] { 0xFF, 0xD8 });
                    int jpegEnd = FindBytes(buffer, bufferPos, new byte[] { 0xFF, 0xD9 }, jpegStart + 2);
                    
                    if (jpegStart >= 0 && jpegEnd > jpegStart && jpegEnd < bufferPos)
                    {
                        // JPEG 데이터 추출
                        int jpegLength = jpegEnd - jpegStart + 2;
                        byte[] jpegData = new byte[jpegLength];
                        Array.Copy(buffer, jpegStart, jpegData, 0, jpegLength);
                        
                        // 메인 스레드에서 텍스처 업데이트
                        UnityMainThreadDispatcher.Instance().Enqueue(() => {
                            UpdateTexture(jpegData);
                        });
                        
                        framesReceived++;
                        
                        // 버퍼 정리
                        int remaining = bufferPos - (jpegEnd + 2);
                        if (remaining > 0)
                        {
                            Array.Copy(buffer, jpegEnd + 2, buffer, 0, remaining);
                            bufferPos = remaining;
                        }
                        else
                        {
                            bufferPos = 0;
                        }
                    }
                    else if (bufferPos > buffer.Length - 100000)
                    {
                        // 버퍼 거의 찼는데 JPEG 못 찾으면 리셋
                        bufferPos = 0;
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"❌ 스트림 에러: {e.Message}");
                isConnected = false;
            }
            finally
            {
                if (stream != null) stream.Close();
                if (tcpClient != null) tcpClient.Close();
                isConnected = false;
            }
            
            if (isStreaming)
            {
                Debug.Log("🔄 재연결 시도 중...");
                Thread.Sleep(2000); // 2초 대기 후 재연결
            }
        }
    }
    
    void UpdateTexture(byte[] jpegData)
    {
        try
        {
            if (texture == null)
            {
                texture = new Texture2D(2, 2);
                texture.filterMode = FilterMode.Bilinear;
            }
            
            if (texture.LoadImage(jpegData))
            {
                if (targetRenderer != null && targetRenderer.material != null)
                {
                    targetRenderer.material.mainTexture = texture;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"텍스처 업데이트 에러: {e.Message}");
        }
    }
    
    int FindBytes(byte[] source, int length, byte[] pattern, int startIndex = 0)
    {
        for (int i = startIndex; i < length - pattern.Length; i++)
        {
            bool found = true;
            for (int j = 0; j < pattern.Length; j++)
            {
                if (source[i + j] != pattern[j])
                {
                    found = false;
                    break;
                }
            }
            if (found) return i;
        }
        return -1;
    }
    
    void OnApplicationQuit()
    {
        StopStreaming();
    }
    
    void OnDestroy()
    {
        StopStreaming();
    }
}
