# fusion/sensor_wrapper.py

import sys
import os
import cv2
import numpy as np
import sounddevice as sd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, 'existing'))

import direction_finder as df
from imu_tracker import SoundTracker


class AudioSensorWrapper:
    def __init__(self):
        self.fs = df.FS
        self.device = 1
        self.tracker = SoundTracker(address=0x69)
        print("✅ 음향 센서 초기화")

    def get_audio_data(self):
        with sd.InputStream(device=self.device, samplerate=self.fs,
                           channels=2, dtype='int32',
                           blocksize=df.SAMPLES_PER_FRAME) as stream:
            recording, _ = stream.read(df.SAMPLES_PER_FRAME)

            rms_value, confidence = df.calculate_snr(recording)

            # RMS → SNR(dB) 변환
            noise_level = 1000000
            if rms_value > noise_level:
                snr_db = 20 * np.log10(rms_value / noise_level)
            else:
                snr_db = 0.0

            snr_db = np.clip(snr_db, 0, 40)

            print(f"    [DEBUG] RMS={rms_value:.0f}, SNR={snr_db:.1f}dB, Conf={confidence:.2f}")

            if confidence > 0.2:
                tau = df.gcc_phat(recording[:, 0], recording[:, 1],
                                 self.fs, df.MAX_DELAY_SAMPLES)
                raw_angle = df.estimate_direction(tau, self.fs,
                                                 df.C_SPEED, df.MIC_DISTANCE)

                self.tracker.update_yaw_combined()
                corrected_angle = raw_angle + self.tracker.current_yaw

                if corrected_angle > 180:
                    corrected_angle -= 360
                elif corrected_angle < -180:
                    corrected_angle += 360

                return {
                    'angle': corrected_angle,
                    'snr': snr_db,
                    'confidence': confidence,
                    'raw_angle': raw_angle
                }
            else:
                return None


class CameraSensorWrapper:
    def __init__(self, stream_url=0):
        self.cap = cv2.VideoCapture(stream_url)
        if not self.cap.isOpened():
            raise ValueError(f"❌ 카메라 열기 실패: {stream_url}")

        self.roi_top_ratio = 0.6
        self.min_gap_width = 50
        self.threshold = 50
        print(f"✅ 카메라 초기화 (ROI: 하단 40%, 최소폭: {self.min_gap_width}px)")

    def get_gaps_with_angles(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        h, w, _ = frame.shape
        roi_top = int(h * self.roi_top_ratio)
        roi_bottom = h

        # ROI 추출 및 이진화
        roi = frame[roi_top:roi_bottom, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blur, self.threshold, 255, cv2.THRESH_BINARY_INV)

        # 노이즈 제거
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 윤곽선 탐지
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        # 틈 필터링
        gaps = []
        for cnt in contours:
            x, y, cnt_w, cnt_h = cv2.boundingRect(cnt)

            if cnt_w >= self.min_gap_width:
                center_x = x + cnt_w / 2
                angle = (center_x - w / 2) / w * 60

                gaps.append({
                    'start': x,
                    'end': x + cnt_w,
                    'center': center_x,
                    'width': cnt_w,
                    'angle': angle,
                    'confidence': min(1.0, cnt_w / 300.0)
                })

        debug_info = {
            'roi_top': roi_top,
            'roi_bottom': roi_bottom,
            'contours': len(contours)
        }

        return gaps, frame, debug_info
