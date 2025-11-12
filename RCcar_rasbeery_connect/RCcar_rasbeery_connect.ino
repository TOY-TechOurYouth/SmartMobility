/*
 * 라즈베리파이로부터 'F', 'B', 'L', 'R', 'S' 명령을 받아 움직입니다.
 */

// ===== 핀 설정 (기존과 동일) =====
#define MOTOR_A_IA 3      // PWM
#define MOTOR_A_IB 11     // PWM
#define MOTOR_A_ENABLE 9  // Enable
#define MOTOR_B_IA 5      // PWM
#define MOTOR_B_IB 6      // PWM
#define MOTOR_B_ENABLE 10 // Enable

// ===== 속도 설정 (기존과 동일) =====
#define MOTOR_SPEED 200
#define TURN_SPEED 150

// ===== 함수 정의 (기존과 동일) =====
void goForward() {
  // Serial.println("Going Forward"); // (디버깅용, 나중에 Pi에서 응답 받을 때 사용)
  analogWrite(MOTOR_A_IA, MOTOR_SPEED);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, MOTOR_SPEED);
  analogWrite(MOTOR_B_IB, 0);
}

void goBackward() {
  // Serial.println("Going Backward");
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, MOTOR_SPEED);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, MOTOR_SPEED);
}

void turnLeft() {
  // Serial.println("Turning Left");
  analogWrite(MOTOR_A_IA, TURN_SPEED);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, TURN_SPEED);
}

void turnRight() {
  // Serial.println("Turning Right");
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, TURN_SPEED);
  analogWrite(MOTOR_B_IA, TURN_SPEED);
  analogWrite(MOTOR_B_IB, 0);
}

void stopMotors() {
  // Serial.println("Stopping");
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, 0);
}

// ===== setup() 함수 수정 =====
void setup() {
  // ⭐ "시리얼 통신"을 9600 속도로 시작합니다. (핵심!)
  // 라즈베리파이와 통신 속도를 맞추는 것입니다.
  Serial.begin(9600);

  // 핀 모드 설정 (기존과 동일)
  pinMode(MOTOR_A_IA, OUTPUT);
  pinMode(MOTOR_A_IB, OUTPUT);
  pinMode(MOTOR_A_ENABLE, OUTPUT);
  pinMode(MOTOR_B_IA, OUTPUT);
  pinMode(MOTOR_B_IB, OUTPUT);
  pinMode(MOTOR_B_ENABLE, OUTPUT);

  // 모터 활성화 (기존과 동일)
  digitalWrite(MOTOR_A_ENABLE, HIGH);
  digitalWrite(MOTOR_B_ENABLE, HIGH);

  // (안전을 위해) 시작은 무조건 정지 상태로
  stopMotors();
}

// ===== loop() 함수 수정 =====
void loop() {
  // ⭐ "만약 라즈베리파이(Serial)로부터 수신한 데이터가 있다면?"
  if (Serial.available() > 0) {
    
    // 1. 데이터를 1글자(char) 읽어옵니다.
    char cmd = Serial.read();

    // 2. 읽어온 글자(cmd)가 무엇인지에 따라 동작을 결정합니다.
    if (cmd == 'F') {       // 'F' (Forward)
      goForward();
    } 
    else if (cmd == 'B') {  // 'B' (Backward)
      goBackward();
    } 
    else if (cmd == 'L') {  // 'L' (Left)
      turnLeft();
    } 
    else if (cmd == 'R') {  // 'R' (Right)
      turnRight();
    } 
    else if (cmd == 'S') {  // 'S' (Stop)
      stopMotors();
    }
  }
  // (데이터가 없으면 아무것도 안 하고 loop()를 반복하며 명령을 기다립니다)
}
