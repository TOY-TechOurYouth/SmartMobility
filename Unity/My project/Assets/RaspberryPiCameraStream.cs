using UnityEngine;
using UnityEngine.Video;

public class RaspberryPiCameraStream : MonoBehaviour
{
    [Header("Video Player")]
    public VideoPlayer videoPlayer;
    
    [Header("Display")]
    public Renderer targetRenderer;
    
    [Header("Stream Settings")]
    public string cameraURL = "http://raspberrypi.local:8080/?action=stream";
    public bool autoStart = true;
    
    [Header("Status")]
    public bool isStreaming = false;
    
    void Start()
    {
        SetupVideoPlayer();
        
        if (autoStart)
        {
            StartStreaming();
        }
    }
    
    void SetupVideoPlayer()
    {
        // VideoPlayer 컴포넌트가 없으면 추가
        if (videoPlayer == null)
        {
            videoPlayer = gameObject.GetComponent<VideoPlayer>();
            if (videoPlayer == null)
            {
                videoPlayer = gameObject.AddComponent<VideoPlayer>();
            }
        }
        
        // 기본 설정
        videoPlayer.source = VideoSource.Url;
        videoPlayer.url = cameraURL;
        videoPlayer.playOnAwake = false;
        videoPlayer.isLooping = true;
        videoPlayer.skipOnDrop = true; // 프레임 드롭 시 스킵
        
        // 렌더링 모드 설정
        videoPlayer.renderMode = VideoRenderMode.MaterialOverride;
        if (targetRenderer != null)
        {
            videoPlayer.targetMaterialRenderer = targetRenderer;
        }
        
        // 오디오 끄기
        videoPlayer.audioOutputMode = VideoAudioOutputMode.None;
        
        // 이벤트 등록
        videoPlayer.prepareCompleted += OnVideoPrepared;
        videoPlayer.errorReceived += OnVideoError;
        videoPlayer.started += OnVideoStarted;
        
        Debug.Log("📹 VideoPlayer 설정 완료");
    }
    
    public void StartStreaming()
    {
        Debug.Log($"📡 스트림 연결 시도: {cameraURL}");
        videoPlayer.Prepare();
    }
    
    public void StopStreaming()
    {
        if (videoPlayer != null && videoPlayer.isPlaying)
        {
            videoPlayer.Stop();
            isStreaming = false;
            Debug.Log("🛑 스트리밍 중지");
        }
    }
    
    void OnVideoPrepared(VideoPlayer vp)
    {
        Debug.Log("✅ 스트림 준비 완료! 재생 시작...");
        vp.Play();
    }
    
    void OnVideoStarted(VideoPlayer vp)
    {
        isStreaming = true;
        Debug.Log($"▶️ 스트리밍 시작! 해상도: {vp.width}x{vp.height}");
    }
    
    void OnVideoError(VideoPlayer vp, string message)
    {
        Debug.LogError($"❌ 비디오 에러: {message}");
        isStreaming = false;
    }
    
    void OnDestroy()
    {
        // 이벤트 해제
        if (videoPlayer != null)
        {
            videoPlayer.prepareCompleted -= OnVideoPrepared;
            videoPlayer.errorReceived -= OnVideoError;
            videoPlayer.started -= OnVideoStarted;
        }
    }
    
    void OnApplicationQuit()
    {
        StopStreaming();
    }
}
