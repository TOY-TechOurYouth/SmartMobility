import numpy as np
from scipy.io import wavfile
import os

def check_wav_channels(file_path):
    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return

    # WAV 파일 읽기
    fs, data = wavfile.read(file_path)

    print(f"--- 파일 정보 ---")
    print(f"샘플링 레이트: {fs} Hz")
    print(f"데이터 형태 (샘플 수, 채널 수): {data.shape}")

    # 스테레오(2채널) 확인
    if len(data.shape) < 2 or data.shape[1] < 2:
        print("결과: 이 파일은 모노(1채널)입니다. 방향 추정을 위해서는 2채널이 필요합니다.")
        return

    # 각 채널 데이터 분리 (int32 데이터를 float로 변환하여 계산)
    left_channel = data[:, 0].astype(float)
    right_channel = data[:, 1].astype(float)

    # 1. 절대값의 평균 (소리의 평균적인 크기)
    l_mean = np.mean(np.abs(left_channel))
    r_mean = np.mean(np.abs(right_channel))

    # 2. 최대값 (피크 수치)
    l_max = np.max(np.abs(left_channel))
    r_max = np.max(np.abs(right_channel))

    print(f"\n--- 채널별 분석 결과 ---")
    print(f"[Left Channel]  평균 크기: {l_mean:>10.2f} | 최대 크기: {l_max:>10.0f}")
    print(f"[Right Channel] 평균 크기: {r_mean:>10.2f} | 최대 크기: {r_max:>10.0f}")

    # 판단 로직
    print(f"\n--- 진단 ---")
    if l_mean < 100 and r_mean < 100:
        print("⚠️ 양쪽 채널 모두 신호가 거의 없습니다. 마이크 볼륨(alsamixer)을 확인하세요.")
    elif l_mean < 100:
        print("⚠️ 왼쪽 채널 신호가 없습니다. 마이크 연결을 확인하세요.")
    elif r_mean < 100:
        print("⚠️ 오른쪽 채널 신호가 없습니다. 마이크 연결을 확인하세요.")
    else:
        diff_ratio = abs(l_mean - r_mean) / max(l_mean, r_mean)
        if diff_ratio > 0.8:
            print("⚠️ 두 채널의 크기 차이가 너무 큽니다. 한쪽 마이크가 가려져 있거나 불량일 수 있습니다.")
        else:
            print("✅ 양쪽 채널 모두 정상적으로 신호를 수신하고 있습니다.")

if __name__ == "__main__":
    check_wav_channels('recorded_audio.wav')