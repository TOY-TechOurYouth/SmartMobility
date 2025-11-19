import numpy as np
import scipy.signal as signal
import sounddevice as sd
import sys
import time

FS = 48000           # 샘플링 레이트 (Hz)
C_SPEED = 343.0      # 공기 중 음속 (m/s, 20°C 기준)
MIC_DISTANCE = 0.048  # 두 마이크 간의 거리 (m). 예: 4.8cm
DURATION = 1.0       # 각 녹음 프레임의 길이 (초)
SAMPLES_PER_FRAME = int(DURATION * FS)

# 최대 시간 지연 계산 (마이크 간 최대 지연 샘플 수)
# 최대 지연 시간 (초) = MIC_DISTANCE / C_SPEED
# 최대 지연 샘플 수 = Max_Delay_Time * FS
MAX_DELAY_SAMPLES = int(MIC_DISTANCE / C_SPEED * FS)

# GCC-PHAT 함수 
def gcc_phat(sig1, sig2, fs, max_delay):
    """
    Generalized Cross-Correlation with Phase Transform (GCC-PHAT)을 사용하여
    두 신호 간의 시간 지연을 샘플 단위로 추정합니다.
    
    Args:
        sig1 (np.array): 첫 번째 마이크 신호 (Left Channel)
        sig2 (np.array): 두 번째 마이크 신호 (Right Channel)
        fs (int): 샘플링 레이트 (Hz)
        max_delay (int): 최대 허용 시간 지연 샘플 수

    Returns:
        float: 추정된 시간 지연 (샘플 단위). sig2가 sig1보다 앞설 경우 양수.
    """
    # FFT 수행
    N = len(sig1)
    nfft = 2 * N # 일반적으로 신호 길이의 2배로 설정
    
    SIG1 = np.fft.rfft(sig1, nfft)
    SIG2 = np.fft.rfft(sig2, nfft)

    # GCC-PHAT 필터 적용 (위상 변환)
    # R_Gcc = (SIG1 * conj(SIG2)) / |SIG1 * conj(SIG2)|
    # 이 과정에서 신호의 크기 정보는 사라지고 위상 정보만 남게 되어 잡음 및 잔향에 강해집니다.
    R_Gcc = SIG1 * np.conjugate(SIG2)
    R_Gcc_Phased = R_Gcc / (np.abs(R_Gcc) + 1e-10) # 1e-10는 0 나누기 방지

    # IFFT 수행 (시간 영역 상호 상관 함수)
    cc = np.fft.irfft(R_Gcc_Phased)
    
    # 시간축 재정렬 및 최대값 찾기
    # IFFT 결과는 0-T/2, -T/2-0 순서로 나타나므로, 이를 시간 지연(-T/2 ~ T/2) 순서로 순환 이동합니다.
    cc_rolled = np.roll(cc, -N // 2)
    
    # 최대 상관값 위치(지연 시간) 찾기
    # 최대 지연 범위 내에서만 탐색합니다.
    # 인덱스 0은 지연 시간 0에 해당합니다.
    delay_index = np.argmax(cc_rolled[N//2 - max_delay : N//2 + max_delay + 1])
    
    # 실제 지연 샘플 수 = 찾은 인덱스 - (최대 지연 범위의 시작점)
    # (N // 2 - max_delay)가 시작점이므로, 찾은 인덱스에서 이 시작점을 빼야 합니다.
    tau_samples = delay_index - max_delay
    
    return tau_samples

# TDOA 및 방향 계산 함수 
def estimate_direction(tau_samples, fs, c_speed, mic_distance):
    """
    샘플 지연 시간을 바탕으로 TDOA를 계산하고, 음원 방향(방위각)을 추정합니다.
    
    Args:
        tau_samples (float): 추정된 시간 지연 (샘플 단위)
        ... (환경 상수)

    Returns:
        float: 방위각 (도 Degree). 0도: 정면, -90도: 왼쪽, +90도: 오른쪽.
    """
    # 지연 시간 (초) 계산
    tau_sec = tau_samples / fs
    
    # 파면이 이동한 거리 차이 (d_diff)
    d_diff = tau_sec * c_speed
    
    # 방위각 (theta) 계산
    # cos(theta) = d_diff / mic_distance
    # -1 <= d_diff / mic_distance <= 1 이 보장되어야 함
    ratio = d_diff / mic_distance
    
    # 유효 범위 [-1.0, 1.0] 클리핑 (부동 소수점 오차 처리)
    if ratio > 1.0: ratio = 1.0
    if ratio < -1.0: ratio = -1.0

    # 아크 코사인으로 각도(라디안) 계산
    theta_rad = np.arccos(ratio)
    
    # 라디안을 도(Degree)로 변환하고 90도 기준으로 조정
    # 마이크 1(Left)이 먼저 들리면 ratio가 양수 -> theta_rad는 0에 가까움 -> 정면(0도)
    # 마이크 2(Right)가 먼저 들리면 ratio가 음수 -> theta_rad는 파이에 가까움 -> 측면(90도)
    
    # 일반적으로 음원 방향 추정에서는 -90도(왼쪽) ~ 90도(오른쪽)를 사용합니다.
    # arccos(ratio) 결과는 [0, 180]도 범위이므로, 
    # 왼쪽: 180 ~ 90도 (arccos 결과) -> -90 ~ 0도 (변환 결과)
    # 정면: 90도 (arccos 결과) -> 0도 (변환 결과)
    # 오른쪽: 0 ~ 90도 (arccos 결과) -> 0 ~ 90도 (변환 결과)
    
    # 직관적인 변환: 각도 = 90 - (theta_rad * 180 / pi)
    # 하지만 더 간단하게는, tau_samples를 기준으로 sin/cos 관계를 뒤집어 계산합니다.
    angle_deg = np.degrees(np.arcsin(ratio))
    
    # 이 결과는 -90(왼쪽) ~ +90(오른쪽)을 나타냅니다.
    # 예시: tau_samples가 양수(L이 먼저 들림) -> ratio 양수 -> angle_deg 양수(오른쪽)
    # 마이크 구성에 따라 결과 부호가 반대로 나올 수 있습니다.
    return angle_deg

# SNR 기반 신뢰도 함수
def calculate_snr(signal_data, noise_threshold=1000):
    """
    신호의 크기를 기반으로 간이 SNR을 계산하고 신뢰도 점수를 부여합니다.
    
    Args:
        signal_data (np.array): 녹음된 신호 데이터 (2채널)
        noise_threshold (int): 잡음으로 간주할 RMS 임계값 (매우 낮은 값)

    Returns:
        tuple: (평균 RMS, 신뢰도 점수)
    """
    # 신호의 평균 제곱근 (RMS) 계산
    # 수정 코드: (데이터가 0일 경우 1e-10을 더하여 0 나누기 방지)
    rms_L = np.sqrt(np.mean(signal_data[:, 0]**2))
    rms_R = np.sqrt(np.mean(signal_data[:, 1]**2))
    avg_rms = (rms_L + rms_R) / 2
    
    # RMS가 임계값보다 클수록 신뢰도가 높다고 가정
    # 신뢰도 점수
    # 0 나누기 방지를 위한 작은 상수 정의
    EPSILON = 1e-10

    # 분모가 0이 되는 것을 방지
    denominator = 2000000 - noise_threshold
    if denominator < EPSILON:
        # 분모가 0에 가까우면 신뢰도 계산 불가능
        return avg_rms, np.nan 

    # 신뢰도 계산 (분모 안정화 버전)
    confidence = np.clip((avg_rms - noise_threshold) / denominator, 0.0, 1.0)
    return avg_rms, confidence


# 메인 실행 루프
def run_direction_finder():
    # 사운드 장치 설정 (이전에 찾은 장치 인덱스를 사용하거나, 재검색)
    try:
        # 이전에 find_i2s_device 함수를 통해 찾은 인덱스를 사용하거나
        # 여기서 기본 입력 장치를 사용합니다.
        # 장치 인덱스를 직접 지정하는 것이 안정적입니다.
        input_device_index = sd.default.device[0] # 기본 입력 장치 사용
        
        # 2채널 입력이 가능한지 확인
        dev_info = sd.query_devices(input_device_index, 'input')
        if dev_info['max_input_channels'] < 2:
            print("선택된 입력 장치가 2채널을 지원하지 않습니다. arecord -l로 장치를 확인하세요.")
            sys.exit(1)
        
        print(f"입력 장치: {dev_info['name']} (Index: {input_device_index})")
        
    except Exception as e:
        print(f"사운드 장치 초기화 오류: {e}")
        sys.exit(1)

    print(f"\n음원 방향 추정 시작 (Ctrl+C로 종료)")
    print(f"   마이크 거리: {MIC_DISTANCE*100} cm")
    print(f"   최대 지연 샘플: {MAX_DELAY_SAMPLES}")
    print("--------------------------------------------------")

    try:
        # 입력 스트림 설정
        with sd.InputStream(samplerate=FS, channels=2, dtype='int32', device=input_device_index) as stream:
            
            while True:
                # 녹음 데이터 프레임 읽기
                # outdata: (SAMPLES_PER_FRAME, 2)
                recording, overflowed = stream.read(SAMPLES_PER_FRAME)
                
                if overflowed:
                    print("버퍼 오버플로우 발생! 샘플링 레이트나 DURATION을 조정하세요.")

                # SNR 및 신뢰도 판단
                avg_rms, confidence = calculate_snr(recording)
                
                # 신뢰도(신호 세기)가 낮으면 계산을 스킵 (잡음만 있을 때)
                if confidence < 0.1: # 10% 미만 신뢰도는 무시
                    print(f"[{time.strftime('%H:%M:%S')}] 💤 낮은 신호 세기 (RMS: {avg_rms:.0f}, Confidence: {confidence:.2f})")
                    continue

                # 채널 분리 (L/R)
                sig_L = recording[:, 0]
                sig_R = recording[:, 1]

                # GCC-PHAT을 이용한 TDOA 계산
                tau_samples = gcc_phat(sig_L, sig_R, FS, MAX_DELAY_SAMPLES)
                
                # 방향 추정
                angle_deg = estimate_direction(tau_samples, FS, C_SPEED, MIC_DISTANCE)
                
                # 결과 출력
                direction_str = "CENTER"
                if angle_deg > 5:
                    direction_str = "RIGHT"
                elif angle_deg < -5:
                    direction_str = "LEFT"
                    
                print(f"[{time.strftime('%H:%M:%S')}] **ANGLE: {angle_deg:+.2f}°** ({direction_str}) | TDOA: {tau_samples} samples | Conf: {confidence:.2f}")

    except KeyboardInterrupt:
        print("\n사용자 요청으로 종료합니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")

if __name__ == "__main__":
    run_direction_finder()