"""
RC카 키보드 원격 조종 프로그램
작성자: 예성
"""

import serial
import time
import sys
import tty
import termios

# 시리얼 포트 설정
SERIAL_PORT = '/dev/ttyUSB0'  # 또는 /dev/ttyUSB0
BAUD_RATE = 9600

# 키 입력 함수 (non-blocking)
def get_key():
    """키보드 입력 받기 (한 글자씩)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def main():
    print("=" * 50)
    print("RC카 원격 조종 프로그램")
    print("=" * 50)

    # 시리얼 포트 연결
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # 아두이노 리셋 대기
        print(f"시리얼 연결 성공: {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f" 시리얼 연결 실패: {e}")
        print("확인 사항:")
        print("   1. 아두이노가 USB로 연결되어 있나요?")
        print("   2. 포트 이름이 맞나요? (ls /dev/tty* 로 확인)")
        print("   3. 권한 문제: sudo usermod -a -G dialout $USER")
        sys.exit(1)

    # 초기 메시지 읽기
    time.sleep(1)
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        print(f"Arduino: {line}")

    print("\n" + "=" * 50)
    print("조작법:")
    print("  W : 전진")
    print("  S : 후진")
    print("  A : 좌회전")
    print("  D : 우회전")
    print("  X : 정지")
    print("  Q : 프로그램 종료")
    print("=" * 50)
    print("\n키를 눌러 조종하세요...\n")

    current_command = 'x'  # 현재 명령

    try:
        while True:
            # 키 입력 받기
            key = get_key().lower()

            # 명령 처리
            if key == 'q':
                print("\n프로그램 종료...")
                ser.write(b'x')  # 정지 명령
                break

            elif key in ['w', 's', 'a', 'd', 'x']:
                # 명령 전송
                ser.write(key.encode())
                current_command = key

                # 명령 표시
                cmd_name = {
                    'w': '⬆️ 전진',
                    's': '⬇️ 후진',
                    'a': '⬅️ 좌회전',
                    'd': '우회전',
                    'x': '⏹️정지'
                }
                print(f"명령: {cmd_name[key]}")

            # 아두이노 응답 읽기
            while ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"  └─ {line}")

            time.sleep(0.05)  # 50ms 대기

    except KeyboardInterrupt:
        print("\n\n프로그램 중단 (Ctrl+C)")
        ser.write(b'x')  # 정지 명령

    finally:
        ser.close()
        print("시리얼 포트 닫힘")

if __name__ == "__main__":
    main()
