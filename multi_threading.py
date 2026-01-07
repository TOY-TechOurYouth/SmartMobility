import threading
import time
import sounddevice as sd
import direction_finder as df
from imu_tracker import SoundTracker

tracker = SoundTracker(address=0x69)
current_goal = None # 현재 이동 중인 목표 각도

def sound_thread():
    print("🔊 소리 감지 스레드 시작")
    with sd.InputStream(device=1, samplerate=df.FS, channels=2, dtype='int32', blocksize=df.SAMPLES_PER_FRAME) as stream:
        while True:
            recording, _ = stream.read(df.SAMPLES_PER_FRAME)
            _, confidence = df.calculate_snr(recording)
            
            # 소리가 확실할 때만 큐에 추가 (이동 중에도 큐에 쌓임)
            if confidence > 0.4:
                tau = df.gcc_phat(recording[:, 0], recording[:, 1], df.FS, df.MAX_DELAY_SAMPLES)
                angle = df.estimate_direction(tau, df.FS, df.C_SPEED, df.MIC_DISTANCE)
                
                tracker.add_sound_target(angle)

def control_thread():
    global current_goal
    print("🏎️ 제어 스레드 시작")
    
    while True:
        # 1. 현재 수행 중인 목표가 없고 큐에 대기 중인 소리가 있다면 하나 꺼냄
        if current_goal is None and tracker.target_queue:
            current_goal = tracker.get_next_target()
            print(f"\n🚀 [NEW TARGET] {current_goal:.1f}° 방향으로 회전 시작")

        # 2. 목표가 설정된 상태라면
        if current_goal is not None:
            tracker.update_yaw_combined()
            error = current_goal - tracker.current_yaw
            if error > 180: error -= 360
            if error < -180: error += 360

            # 1단계: 방향 맞추기 (회전)
            if abs(error) > 5.0:
                # 여기서 실제 모터 회전 명령을 내릴 수 있습니다 (예: turn_left() 또는 turn_right())
                print(f"\r[ROTATING] 목표: {current_goal:5.1f}° | 현재: {tracker.current_yaw:5.1f}° | 오차: {error:+.1f}°", end="")
            
            # 2단계: 방향이 맞으면 10초 동안 직진
            else:
                print(f"\n✅ 방향 일치! 10초 동안 직진 이동합니다...")
                
                # --- 실제 모터 제어 예시 ---
                # motors.forward()  # 모터 직진 시작
                
                # 10초를 쪼개서 대기 (중간에 종료 체크 가능하도록)
                for i in range(10):
                    print(f"\r[DRIVING] 전진 중... {10-i}초 남음", end="")
                    time.sleep(1)
                
                # motors.stop()     # 모터 정지
                # -------------------------
                
                print(f"\n🏁 도착 완료! {current_goal:.1f}° 지점 데이터 삭제 및 다음 소리 대기.")
                
                # 직진까지 끝났으므로 목표를 초기화 (데이터 삭제 효과)
                # 다음 루프에서 큐에 있는 다음 소리(2번째 소리)를 자동으로 가져옴
                current_goal = None 
                
        time.sleep(0.05)

if __name__ == "__main__":
    t_audio = threading.Thread(target=sound_thread, daemon=True)
    t_motor = threading.Thread(target=control_thread, daemon=True)
    t_audio.start()
    t_motor.start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n사용자 종료")