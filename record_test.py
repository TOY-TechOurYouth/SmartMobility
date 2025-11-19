import subprocess
import time
import os

# 설정 변수 
# 2 채널
CHANNELS = 2
# 녹음 시간 (초)
DURATION = 10 
# 저장할 파일
FILE_NAME = "recorded_audio.wav"
# 마이크 카드 이름의 고유 식별자 
CARD_ID = "googlevoicehat"

# 두 개의 마이크 연결 시 채널이 분리된 하나의 통합된 오디오 시스템으로 인식
# 재부팅 시 카드 번호 자동 감지 함수
def get_mic_card_number():
    try:
        # 'arecord -l' 명령을 실행하여 출력
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, check=True)
        
        # 출력에서 마이크 ID를 포함하는 줄 찾아 카드 번호 추출
        for line in result.stdout.splitlines():
            if CARD_ID in line:
                # 'card X:' 에서 숫자 X만 추출
                card_number = line.split(':')[0].split('card ')[1]
                return card_number
        
        print(f"오류: '{CARD_ID}'를 포함하는 마이크 장치를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"오류: arecord 명령 실행 중 문제 발생. {e}")
        return None

def record_audio():
    # 녹음 전 카드 번호를 먼저 감지
    CARD_NUMBER = get_mic_card_number()
    if CARD_NUMBER is None:
        return # 카드 번호를 못 찾으면 종료

    print(f"마이크 카드 번호 자동 감지: Card {CARD_NUMBER}")
    print(f"[{CHANNELS}채널] 마이크 녹음을 시작합니다 ({DURATION}초)...")
    
    # 이전에 녹음된 파일이 있다면 삭제
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)

    # 녹음 명령어 구성 
    record_command = [
        "arecord",
        f"-Dplughw:{CARD_NUMBER},0",  # 감지된 카드 번호 사용
        f"-c{CHANNELS}",
        "-r48000",
        "-fS32_LE",
        "-t", "wav",
        f"-d{DURATION}",
        FILE_NAME
    ]
    
    # 서브프로세스로 명령어 실행
    try:
        process = subprocess.run(record_command, check=True, capture_output=True, text=True)
        print(f"녹음 완료! 파일: {FILE_NAME}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n--- 오류 발생 ---")
        print(f"녹음 중 오류가 발생했습니다. 하드웨어 연결 및 설정을 다시 확인하세요.")
        print(f"Stderr: {e.stderr}")
        print(f"-----------------\n")

if __name__ == "__main__":
    record_audio()