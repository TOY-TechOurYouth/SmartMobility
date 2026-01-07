import time
import board
import adafruit_icm20x
import numpy as np
import heapq  # 우선순위 큐를 위해 추가

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
        self.priority_queue = []  # (신뢰도, 목표각도)를 담을 리스트
        self.is_active = False
        self.last_time = time.time()
        self.alpha = 0.95 

    def update_yaw_combined(self):
        # 상보필터 로직 (기존과 동일)
        try:
            gyro_z = self.icm.gyro[2] 
            now = time.time()
            dt = now - self.last_time
            self.last_time = now
            gyro_yaw = self.current_yaw + np.degrees(gyro_z) * dt
            mag_x, mag_y, _ = self.icm.magnetic
            mag_heading = np.degrees(np.arctan2(mag_y, mag_x))
            self.current_yaw = self.alpha * gyro_yaw + (1 - self.alpha) * mag_heading
            self.current_yaw %= 360
        except:
            pass
        return self.current_yaw

    def add_sound_target(self, relative_angle, confidence):
        """소리 방향과 신뢰도를 함께 저장 (신뢰도 높은 순 정렬)"""
        self.update_yaw_combined()
        absolute_target = (self.current_yaw + relative_angle) % 360
        
        # heapq는 최소 힙이므로, 큰 값이 먼저 나오게 하기 위해 confidence에 -를 붙임
        heapq.heappush(self.priority_queue, (-confidence, absolute_target))
        print(f"\n📥 소리 감지 (신뢰도: {confidence:.2f}) -> 큐 저장")

    def get_next_target(self):
        """가장 신뢰도가 높은 목표를 꺼냄"""
        if self.priority_queue:
            neg_conf, target = heapq.heappop(self.priority_queue)
            self.is_active = True
            return target, -neg_conf # (목표각도, 원래 신뢰도) 반환
        self.is_active = False
        return None, None