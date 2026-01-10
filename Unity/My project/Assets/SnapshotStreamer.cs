using System.Collections;
using UnityEngine;

public class SnapshotStreamer : MonoBehaviour
{
    [Header("Stream Settings")]
    public string snapshotURL = "http://raspberrypi.local:8080/?action=snapshot";
    public float refreshRate = 30f;
    
    [Header("Display")]
    public Renderer targetRenderer;
    
    private Texture2D texture;
    private bool isStreaming = false;
    
    void Start()
    {
        StartStreaming();
    }
    
    public void StartStreaming()
    {
        if (!isStreaming)
        {
            isStreaming = true;
            StartCoroutine(StreamSnapshots());
            Debug.Log($"📡 스트리밍 시작: {snapshotURL}");
        }
    }
    
    IEnumerator StreamSnapshots()
    {
        float interval = 1f / refreshRate;
        
        while (isStreaming)
        {
#pragma warning disable CS0618 // WWW is obsolete but works
            WWW www = new WWW(snapshotURL);
            
            yield return www;
            
            if (string.IsNullOrEmpty(www.error))
            {
                texture = www.texture;
                
                if (targetRenderer != null && texture != null)
                {
                    targetRenderer.material.mainTexture = texture;
                    Debug.Log($"✅ 프레임 수신! {texture.width}x{texture.height}");
                }
            }
            else
            {
                Debug.LogError($"❌ 에러: {www.error}");
                yield return new WaitForSeconds(2f);
            }
#pragma warning restore CS0618
            
            yield return new WaitForSeconds(interval);
        }
    }
    
    void OnApplicationQuit()
    {
        isStreaming = false;
        StopAllCoroutines();
    }
}