import time
import board
import adafruit_icm20x
import numpy as np
from collections import deque

class SoundTracker:
    def __init__(self, address=0x69):
        try:
            i2c = board.I2C()
            self.icm = adafruit_icm20x.ICM20948(i2c, address=address)
            print(f"✅ IMU 연결 성공")
        except Exception as e:
            print(f"❌ IMU 연결 실패: {e}")
            raise

        self.current_yaw = 0.0
        self.target_queue = deque()  # 소리 방향을 저장할 큐 (최대 개수 제한 가능)
        self.is_active = False       # 현재 이동/회전 중인지 여부
        self.last_time = time.time()
        self.alpha = 0.95 

    def update_yaw_combined(self):
        # (기존 상보필터 로직 동일)
        gyro_z = self.icm.gyro[2] 
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        gyro_yaw = self.current_yaw + np.degrees(gyro_z) * dt
        mag_x, mag_y, _ = self.icm.magnetic
        mag_heading = np.degrees(np.arctan2(mag_y, mag_x))
        self.current_yaw = self.alpha * gyro_yaw + (1 - self.alpha) * mag_heading
        self.current_yaw %= 360
        return self.current_yaw

    def add_sound_target(self, relative_angle):
        """새로운 소리가 들리면 큐에 추가"""
        self.update_yaw_combined()
        absolute_target = (self.current_yaw + relative_angle) % 360
        self.target_queue.append(absolute_target)
        print(f"\n📥 소리 감지! 큐에 저장됨: {absolute_target:.1f}° (현재 큐 크기: {len(self.target_queue)})")

    def get_next_target(self):
        """도착 후 다음 목표를 가져옴"""
        if self.target_queue:
            next_target = self.target_queue.popleft() # 첫 번째 소리 삭제 및 추출
            self.is_active = True
            return next_target
        self.is_active = False
        return None