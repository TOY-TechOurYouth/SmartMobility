import threading
import time
import sounddevice as sd
import direction_finder as df
from imu_tracker import SoundTracker

tracker = SoundTracker(address=0x69)
current_goal = None 
current_conf = 0.0

def sound_thread():
    print("🔊 소리 감지 스레드 시작")
    with sd.InputStream(device=1, samplerate=df.FS, channels=2, dtype='int32', blocksize=df.SAMPLES_PER_FRAME) as stream:
        while True:
            recording, _ = stream.read(df.SAMPLES_PER_FRAME)
            _, confidence = df.calculate_snr(recording)
            
            if confidence > 0.4:
                tau = df.gcc_phat(recording[:, 0], recording[:, 1], df.FS, df.MAX_DELAY_SAMPLES)
                angle = df.estimate_direction(tau, df.FS, df.C_SPEED, df.MIC_DISTANCE)
                
                # [수정] confidence 인자를 함께 전달
                tracker.add_sound_target(angle, confidence)

def control_thread():
    global current_goal, current_conf
    print("🏎️ 제어 스레드 시작")
    
    while True:
        # target_queue 대신 priority_queue 확인
        if current_goal is None and tracker.priority_queue:
            # 신뢰도와 목표를 함께 가져옴
            current_goal, current_conf = tracker.get_next_target()
            print(f"\n🚀 [NEW TARGET] 신뢰도 {current_conf:.2f} | {current_goal:.1f}° 방향 회전 시작")

        if current_goal is not None:
            tracker.update_yaw_combined()
            error = current_goal - tracker.current_yaw
            if error > 180: error -= 360
            if error < -180: error += 360

            if abs(error) > 5.0:
                print(f"\r[ROTATING] 목표: {current_goal:5.1f}° | 신뢰도: {current_conf:.2f} | 오차: {error:+.1f}°", end="")
            else:
                print(f"\n✅ 방향 일치! 10초 동안 직진 이동합니다...")
                for i in range(10):
                    print(f"\r[DRIVING] 전진 중... {10-i}초 남음", end="")
                    time.sleep(1)
                
                print(f"\n🏁 도착 완료! {current_goal:.1f}° 데이터 삭제.")
                current_goal = None 
                current_conf = 0.0
                
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