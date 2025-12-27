import serial
import time
import curses  # 키보드 입력을 실시간으로 받기 위한 라이브러리

# --- 아두이노 연결 설정 ---
ARDUINO_PORT = '/dev/ttyUSB0'  # 포트 이름 확인!
BAUDRATE = 9600

try:
    arduino = serial.Serial(port=ARDUINO_PORT, baudrate=BAUDRATE, timeout=.1)
    # print(f"{ARDUINO_PORT} 포트로 아두이노 연결 성공!") # curses 사용 시 print는 주석 처리
    time.sleep(2)  # 아두이노 재부팅 시간
except serial.SerialException as e:
    print(f"아두이노 연결 실패: {e}") # curses 시작 전이라 print 가능
    print("포트 이름을 확인하세요.")
    exit()
# ---------------------------------------------

def send_command(command):
    """아두이노에 1바이트 명령을 보냅니다."""
    arduino.write(command.encode())
    # print(f"명령 전송: {command}") # curses 사용 시 print는 주석 처리


def main(stdscr):
    """메인 조종 함수"""
    # curses 설정: 키가 눌리는 즉시 반응하고, 화면에 입력값을 표시하지 않음
    stdscr.nodelay(True)  # getch()가 기다리지 않도록 논블로킹 모드
    
    last_command = 'S' # 마지막으로 보낸 명령 (중복 전송 방지)

    while True:
        try:
            # === 화면 그리기 (매 루프마다 새로 그림) ===
            stdscr.clear() # 1. 화면을 깨끗이 지운다
            
            # 2. 메뉴를 그린다 (print 대신 addstr 사용)
            stdscr.addstr(0, 0, "=== RC카 키보드 조종 시작 ===")
            stdscr.addstr(1, 0, "F: 전진 | B: 후진 | L: 좌회전 | R: 우회전")
            stdscr.addstr(2, 0, "S: 정지 (또는 키를 떼면 자동 정지)")
            stdscr.addstr(3, 0, "Q: 종료")
            stdscr.addstr(4, 0, "-----------------------------")
            stdscr.addstr(6, 0, f"현재 전송된 명령: {last_command}   ") # 3. 현재 상태 표시
            # === 화면 그리기 끝 ===

            # 키보드 입력 받기 (키가 안 눌렸으면 -1 반환)
            key = stdscr.getch()
            
            command_to_send = None

            # 'F', 'B', 'L', 'R', 'S' 키를 아두이노 명령과 1:1로 매핑합니다.
            if key == ord('f') or key == ord('F'):
                command_to_send = 'F' # 'F' 키 -> 'F' 명령
            elif key == ord('b') or key == ord('B'):
                command_to_send = 'B' # 'B' 키 -> 'B' 명령
            elif key == ord('l') or key == ord('L'):
                command_to_send = 'L' # 'L' 키 -> 'L' 명령
            elif key == ord('r') or key == ord('R'):
                command_to_send = 'R' # 'R' 키 -> 'R' 명령
            elif key == ord('s') or key == ord('S'): 
                command_to_send = 'S' # 'S' 키 -> 'S' 명령
            elif key == ord('q') or key == ord('Q'): # 'Q'로 종료
                break  # 'q' 누르면 루프 탈출
            elif key == -1: # 키가 눌리지 않았을 때 (손을 뗐을 때)
                if last_command != 'S':
                    command_to_send = 'S' # 키를 떼면 정지
                
            if command_to_send and command_to_send != last_command:
                send_command(command_to_send)
                last_command = command_to_send
                # print(f"명령: {command_to_send}") # 이 print()가 화면을 깨트리는 주범!
            
            stdscr.refresh() # 4. 변경된 화면을 적용한다

            # CPU 부담을 줄이기 위해 잠시 대기
            time.sleep(0.05) # 50ms (1초에 20번 체크)

        except KeyboardInterrupt:
            break
        except Exception as e:
            # stdscr.clear() # 화면을 지우고 오류 메시지 출력
            # print(f"오류 발생: {e}") # curses 종료 후라 print 가능
            break # 오류 발생 시 루프 탈출

    # 종료 전 모터 정지
    send_command('S')
    arduino.close()
    # print("시리얼 연결 종료.") # curses 종료 후라 print 가능

# curses.wrapper를 사용해 터미널 설정을 안전하게 복구
if __name__ == "__main__":
    print("아두이노 연결 시도...")
    curses.wrapper(main)
    print("프로그램 종료.")