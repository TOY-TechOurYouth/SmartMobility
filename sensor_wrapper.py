# fusion/sensor_wrapper.py

import sys
import os
import cv2
import numpy as np
from ultralytics import YOLO
import sounddevice as sd

# existing 폴더 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, 'existing'))

import direction_finder as df
from imu_tracker import SoundTracker


class AudioSensorWrapper:
    """
    기존 multi_threading.py 로직 래핑
    """
    def __init__(self):
        self.fs = df.FS
        self.device = 1
        self.tracker = SoundTracker(address=0x69)
        print("✅ 음향 센서 초기화")

    def get_audio_data(self):
        """
        음향 데이터 수집

        Returns:
            {
                'angle': float,
                'snr': float,
                'confidence': float,
                'raw_angle': float
            }
            또는 None
        """
        with sd.InputStream(device=self.device, samplerate=self.fs,
                           channels=2, dtype='int32',
                           blocksize=df.SAMPLES_PER_FRAME) as stream:
            recording, _ = stream.read(df.SAMPLES_PER_FRAME)

            snr_value, confidence = df.calculate_snr(recording)

            # 디버그
            print(f"    [DEBUG] SNR={snr_value:.1f}dB, Conf={confidence:.2f}")

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
                    'snr': snr_value,
                    'confidence': confidence,
                    'raw_angle': raw_angle
                }
            else:
                return None


class CameraSensorWrapper:
    """
    기존 yolo_gap.py 로직 래핑
    """
    def __init__(self, stream_url="http://172.20.10.6:8080/?action=stream"):
        self.model = YOLO("yolov8n.pt")
        self.cap = cv2.VideoCapture(stream_url)
        self.roi_top_ratio = 0.6
        self.min_gap_pixels = 120
        print("✅ 카메라 센서 초기화")

    def get_gaps_with_angles(self):
        """
        틈 탐지

        Returns:
            gaps: 틈 리스트
            frame: 프레임
        """
        ret, frame = self.cap.read()
        if not ret:
            return [], None

        h, w, _ = frame.shape

        # YOLO 탐지
        frame_small = cv2.resize(frame, (640, 360))
        results = self.model(frame_small, imgsz=640, conf=0.25, verbose=False)[0]

        # 스케일 복원
        scale_x = w / 640
        scale_y = h / 360

        obstacle_boxes = []
        for box in results.boxes.xyxy:
            x1, y1, x2, y2 = box.tolist()
            x1 *= scale_x
            x2 *= scale_x
            y1 *= scale_y
            y2 *= scale_y
            obstacle_boxes.append((x1, y1, x2, y2))

        # Gap 탐지
        gaps_raw, _, _, _ = self._detect_gaps_from_boxes(h, w, obstacle_boxes)

        # 구조화
        gaps = []
        for (u1, u2) in gaps_raw:
            center = (u1 + u2) / 2
            width = u2 - u1
            angle = ((center - w/2) / (w/2)) * 30
            confidence = min(1.0, width / 300.0)

            gaps.append({
                'start': u1,
                'end': u2,
                'center': center,
                'width': width,
                'angle': angle,
                'confidence': confidence
            })

        return gaps, frame

    def _detect_gaps_from_boxes(self, h, w, boxes):
        """Gap 탐지 로직"""
        roi_top = int(h * self.roi_top_ratio)
        roi_bottom = h

        occ = np.zeros(w, dtype=np.uint8)

        for (x1, y1, x2, y2) in boxes:
            if y2 < roi_top or y1 > roi_bottom:
                continue
            u1 = max(0, int(x1))
            u2 = min(w, int(x2))
            occ[u1:u2] = 1

        gaps = []
        in_gap = False
        start = 0
        for x in range(w):
            if occ[x] == 0 and not in_gap:
                in_gap = True
                start = x
            elif (occ[x] == 1 or x == w - 1) and in_gap:
                end = x if occ[x] == 1 else x + 1
                if end - start >= self.min_gap_pixels:
                    gaps.append((start, end))
                in_gap = False

        return gaps, roi_top, roi_bottom, occ
