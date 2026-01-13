import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import cv2
import threading
from flask import Flask, Response
from fusion.sensor_wrapper import AudioSensorWrapper, CameraSensorWrapper
from fusion.adaptive_fusion import AdaptiveFusion

# 전역 변수
latest_frame = None
latest_result = None
frame_lock = threading.Lock()

app = Flask(__name__)


def audio_loop():
    """음향 센서 전용 루프 (별도 스레드)"""
    global latest_result

    audio_sensor = AudioSensorWrapper()
    print("✅ 음향 센서 시작")

    while True:
        try:
            audio_data = audio_sensor.get_audio_data()

            if audio_data:
                with frame_lock:
                    if latest_result:
                        latest_result['audio'] = audio_data
        except Exception as e:
            print(f"음향 오류: {e}")
            time.sleep(0.1)


def camera_loop():
    """카메라 센서 전용 루프 (메인 스레드)"""
    global latest_frame, latest_result

    print("🚀 카메라 시스템 시작\n")

    camera_sensor = CameraSensorWrapper(
        stream_url="http://172.20.10.6:8080/?action=stream"
    )
    fusion = AdaptiveFusion()

    print("✅ 카메라 초기화 완료\n")

    frame_count = 0
    yolo_interval = 3  # YOLO는 3프레임마다만 실행
    last_gaps = []
    last_debug = None

    try:
        while True:
            frame_count += 1

            # === 프레임 읽기 (빠름!) ===
            ret, frame = camera_sensor.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # === YOLO는 N프레임마다만 (느림 방지) ===
            if frame_count % yolo_interval == 0:
                gaps, _, debug_info = camera_sensor.get_gaps_with_angles()
                if gaps:
                    last_gaps = gaps
                    last_debug = debug_info

            # === 융합 (최신 데이터) ===
            result_data = {
                'audio': None,
                'gaps': last_gaps,
                'result': None
            }

            with frame_lock:
                if latest_result and latest_result.get('audio'):
                    result_data['audio'] = latest_result['audio']

            # 융합 실행
            if result_data['audio'] and last_gaps:
                try:
                    result_data['result'] = fusion.fuse(
                        result_data['audio'],
                        last_gaps
                    )
                except:
                    pass

            # === 시각화 (빠름!) ===
            vis_frame = visualize_fast(
                frame,
                last_gaps,
                result_data['result'],
                result_data['audio'],
                last_debug
            )

            # 전역 변수 업데이트
            with frame_lock:
                latest_frame = vis_frame
                latest_result = result_data

            # === 짧은 대기만! ===
            time.sleep(0.01)  # 0.3초 → 0.01초 (100 FPS 가능)

    except Exception as e:
        print(f"\n❌ 카메라 오류: {e}")
    finally:
        camera_sensor.cap.release()
        print("\n⏹️  카메라 루프 종료")


def visualize_fast(frame, gaps, result, audio_data, debug_info):
    """최적화된 시각화 (간단하게!)"""
    vis = frame.copy()
    h, w, _ = vis.shape

    roi_top = debug_info['roi_top'] if debug_info else int(h * 0.6)
    roi_bottom = h
    # === 1. 틈 시각화 ===
    if gaps:
        overlay = vis.copy()

        for i, gap in enumerate(gaps):
            is_best = (result and gap == result['best_gap'])

            if is_best:
                color = (0, 255, 0)      # 초록
                thickness = 6
            elif i == 1:
                color = (0, 165, 255)    # 주황
                thickness = 4
            else:
                color = (255, 200, 0)    # 하늘색
                thickness = 2

            # 채우기
            cv2.rectangle(overlay,
                         (int(gap['start']), roi_top),
                         (int(gap['end']), roi_bottom),
                         color, -1)

            # 테두리
            cv2.rectangle(vis,
                         (int(gap['start']), roi_top),
                         (int(gap['end']), roi_bottom),
                         color, thickness)

            # 순위 번호
            rank_text = f"#{i+1}"
            cv2.putText(vis, rank_text,
                       (int(gap['center']) - 20, roi_top - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)

        # 반투명 효과
        vis = cv2.addWeighted(vis, 0.5, overlay, 0.5, 0)

    # === 2. ROI 경계선 ===
    cv2.line(vis, (0, roi_top), (w, roi_top), (0, 255, 255), 2)
    cv2.putText(vis, "ROI", (10, roi_top - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # === 3. 상태 정보 ===
    cv2.rectangle(vis, (5, 5), (450, 100), (0, 0, 0), -1)
    cv2.rectangle(vis, (5, 5), (450, 100), (255, 255, 255), 2)

    if gaps:
        best_gap = result['best_gap'] if result else gaps[0]
        gap_text = f"Best: {best_gap['angle']:+.1f}deg ({best_gap['width']:.0f}px)"
        cv2.putText(vis, gap_text, (15, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(vis, "NO GAP DETECTED", (15, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    if audio_data:
        mode = result['mode'] if result else "N/A"
        mode_text = "AUDIO" if mode == 'audio_trust' else "VISUAL"
        audio_text = f"{mode_text} | {audio_data['angle']:+.1f}deg | SNR:{audio_data['snr']:.1f}dB"
        color = (0, 255, 0) if audio_data['snr'] > 10 else (0, 165, 255)
        cv2.putText(vis, audio_text, (15, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    else:
        cv2.putText(vis, "No Audio", (15, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)

    return vis

def generate_frames():
    """MJPEG 스트리밍 (최적화)"""
    while True:
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.01)
                continue
            frame = latest_frame.copy()

        # JPEG 인코딩 (품질 낮춰서 속도 UP)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.02)  # 50 FPS


@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>RC Car Vision - Fast</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                margin: 0;
                padding: 10px;
                background: #000;
                color: #0f0;
                font-family: monospace;
                text-align: center;
            }
            h1 {
                font-size: 1.5em;
                margin: 10px 0;
            }
            img {
                width: 100%;
                max-width: 1280px;
                border: 2px solid #0f0;
            }
            .info {
                font-size: 0.9em;
                margin-top: 10px;
                color: #888;
            }
        </style>
    </head>
    <body>
        <h1>🚗 RC CAR - LIVE</h1>
        <img src="/video_feed" alt="Live">
        <div class="info">
            ✅ 초록=1순위 | ⚪ 회색=기타 | 🔊 AUD>15dB | 👁️ VIS<15dB
        </div>
    </body>
    </html>
    """


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    # 음향 센서 별도 스레드
    audio_thread = threading.Thread(target=audio_loop, daemon=True)
    audio_thread.start()
    time.sleep(2)  # 센서 초기화 대기

    # 카메라 루프 별도 스레드
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    time.sleep(2)

    # Flask 서버 시작
    print("\n" + "=" * 60)
    print("🌐 고속 웹 스트리밍 서버!")
    print("=" * 60)
    print("\n📺 http://172.20.10.6:5000")
    print("\n🚀 최적화:")
    print("   • 멀티스레딩 (음향 | 카메라 분리)")
    print("   • YOLO 3프레임마다")
    print("   • 대기시간 최소화 (0.01초)")
    print("   • 간소화된 시각화")
    print("\n종료: Ctrl+C\n")

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
