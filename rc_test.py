import serial
import time

# 2단계에서 확인한 포트 이름으로 수정!
ARDUINO_PORT = '/dev/ttyUSB0'
# 아두이노 코드의 Serial.begin(9600)과 속도를 맞춥니다.
BAUDRATE = 9600

try:
    # 1. 아두이노와 시리얼 연결
    arduino = serial.Serial(port=ARDUINO_PORT, baudrate=BAUDRATE, timeout=.1)
    print(f"{ARDUINO_PORT} 포트로 아두이노 연결 성공!")
    # 연결 후 아두이노가 재부팅할 시간을 2초 줍니다.
    time.sleep(2)

except serial.SerialException as e:
    print(f"아두이노 연결 실패: {e}")
    print("포트 이름을 확인하세요. ('/dev/ttyUSB0'일 수도 있습니다)")
    exit() # 연결 실패 시 프로그램 종료

def send_command(command):
    """아두이노에 1바이트(1글자) 명령을 보냅니다."""
    # 'F' 같은 문자를 b'F' (바이트) 형태로 인코딩해서 보냅니다.
    arduino.write(command.encode())
    print(f"명령 전송: {command}")
    # (선택 사항) 아두이노로부터 응답을 기다릴 수 있습니다.
    # response = arduino.readline().decode().strip()
    # if response:
    #     print(f"아두이노 응답: {response}")
    time.sleep(0.1) # 아두이노가 명령을 처리할 약간의 시간

# --- 테스트 시작 ---
try:
    print("테스트를 시작합니다. (Ctrl+C를 눌러 중지)")

    print("\n3초 뒤 [전진(F)] 명령을 보냅니다...")
    time.sleep(3)
    send_command('F')  # 'F' 전송 -> 아두이노가 goForward() 실행

    print("2초간 전진 후 [정지(S)]")
    time.sleep(2)
    send_command('S')  # 'S' 전송 -> 아두이노가 stopMotors() 실행

    print("\n1초 뒤 [좌회전(L)] 명령을 보냅니다...")
    time.sleep(1)
    send_command('L')  # 'L' 전송 -> 아두이노가 turnLeft() 실행

    print("1초간 좌회전 후 [정지(S)]")
    time.sleep(1)
    send_command('S')

    print("\n테스트 완료. 프로그램을 종료합니다.")

except KeyboardInterrupt:
    # Ctrl+C로 강제 종료 시
    print("\n수동 정지! 모터를 멈춥니다.")
    send_command('S')

finally:
    # 프로그램이 어떻게 끝나든 항상 정지 명령을 보내고 연결을 닫습니다.
    send_command('S')
    arduino.close()
    print("시리얼 연결을 종료했습니다.")