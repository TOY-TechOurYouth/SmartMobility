# main_fusion.pynan

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import cv2
from fusion.sensor_wrapper import AudioSensorWrapper, CameraSensorWrapper
from fusion.adaptive_fusion import AdaptiveFusion


def main():
    print("🚀 2센서 적응형 융합 시스템 시작\n")

    # 센서 초기화
    print("센서 초기화 중...")
    audio_sensor = AudioSensorWrapper()
    camera_sensor = CameraSensorWrapper(stream_url="http://172.20.10.6:8080/?action=stram")

    # 융합 엔진
    fusion = AdaptiveFusion()

    print("✅ 초기화 완료\n")

    frame_count = 0

    try:
        while True:
            frame_count += 1
            print(f"\n{'=' * 60}")
            print(f"프레임 #{frame_count}")
            print(f"{'=' * 60}")

            # === 1. 센서 데이터 수집 ===

            # 음향
            audio_data = audio_sensor.get_audio_data()

            if audio_data:
                print(f"🔊 음향 감지:")
                print(f"   원래 각도: {audio_data['raw_angle']:.1f}°")
                print(f"   보정 각도: {audio_data['angle']:.1f}°")
                print(f"   SNR: {audio_data['snr']:.1f}dB")
                print(f"   신뢰도: {audio_data['confidence']:.2f}")
            else:
                print("🔇 음향 없음 (대기 중...)")
                time.sleep(0.5)
                continue

            # 틈
            gaps, frame = camera_sensor.get_gaps_with_angles()

            if gaps:
                print(f"\n📷 틈 {len(gaps)}개 탐지:")
                for i, gap in enumerate(gaps):
                    print(f"   #{i}: 각도 {gap['angle']:+.1f}°, 폭 {gap['width']:.0f}px")
            else:
                print("\n📷 틈 없음")
                time.sleep(0.5)
                continue

            # === 2. 융합 실행 ===
            result = fusion.fuse(audio_data, gaps)

            if result:
                # === 3. 시각화 ===
                vis_frame = visualize_result(frame, gaps, result, audio_data)

                cv2.imshow("Adaptive Fusion", vis_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            time.sleep(0.3)  # 0.3초마다

    except KeyboardInterrupt:
        print("\n\n⏹️  종료")

    finally:
        camera_sensor.cap.release()
        cv2.destroyAllWindows()


def visualize_result(frame, gaps, result, audio_data):
    """
    결과 시각화
    """
    vis = frame.copy()
    h, w, _ = vis.shape

    # 각 틈 표시
    for i, gap_score in enumerate(result['all_scores']):
        gap = gap_score['gap']

        # 색상 (1순위=초록, 나머지=노랑)
        if gap == result['best_gap']:
            color = (0, 255, 0)  # 초록
            thickness = 5
        else:
            color = (0, 255, 255)  # 노랑
            thickness = 2

        # 틈 박스
        y_top = int(h * 0.6)
        cv2.rectangle(vis,
                      (int(gap['start']), y_top),
                      (int(gap['end']), h),
                      color, thickness)

        # 점수 표시
        cv2.putText(vis,
                    f"#{i + 1}: {gap_score['total_score']:.2f}",
                    (int(gap['center']), y_top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, color, 2)

    # 모드 표시
    mode_text = "🔊 음향 신뢰" if result['mode'] == 'audio_trust' else "📷 시각 신뢰"
    cv2.putText(vis, mode_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2)

    # SNR 표시
    cv2.putText(vis, f"SNR: {audio_data['snr']:.1f}dB",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    # 음향 방향 표시
    cv2.putText(vis, f"Audio: {audio_data['angle']:+.1f}°",
                (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    return vis


if __name__ == "__main__":
    main()
