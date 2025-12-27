/**
 * @file arduino_rc_ultra.ino
 * @brief 초음파 센서 기반 능동형 장애물 회피 제어
 * * [수정 사항]
 * 1. 기존 파일과의 충돌을 방지하기 위해 중복 정의된 함수 및 변수 정리
 * 2. 폴더 내 다른 .ino 파일이 있으면 컴파일 에러가 발생하므로 단일 파일로 구성함
 */

// --- 핀 설정 ---
const int trigPin = 12;
const int echoPin = 13;

// L9110S 모터 핀 설정 (배선에 맞춰 확인 필요)
#define MOTOR_A_IA 3
#define MOTOR_A_IB 11
#define MOTOR_B_IA 5
#define MOTOR_B_IB 6

// --- 설정값 ---
const int DISTANCE_THRESHOLD = 15; // cm 단위
const int MOTOR_VAL = 200;         // 변수명 충돌 방지를 위해 VAL로 명명

// --- 상태 변수 ---
char currentStatus = 'S'; 

void setup() {
  Serial.begin(9600);
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  pinMode(MOTOR_A_IA, OUTPUT);
  pinMode(MOTOR_A_IB, OUTPUT);
  pinMode(MOTOR_B_IA, OUTPUT);
  pinMode(MOTOR_B_IB, OUTPUT);
  
  stopMotors();
}

void loop() {
  long distance = getDistance();

  // 1. 능동적 안전 장치 (전진 중 장애물 발견 시 즉시 정지)
  if (currentStatus == 'F' && distance > 0 && distance < DISTANCE_THRESHOLD) {
    stopMotors();
    currentStatus = 'S';
  }

  // 2. 시리얼 명령 처리
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    // 전진 명령 시 거리가 가까우면 명령 무시 및 정지
    if (command == 'F' && distance > 0 && distance < DISTANCE_THRESHOLD) {
      stopMotors();
      currentStatus = 'S';
    } 
    else {
      executeCommand(command);
      currentStatus = command;
    }
  }
  
  delay(10); 
}

/**
 * @brief 초음파 센서 거리 측정 함수
 * @return distance (cm)
 */
long getDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000); 
  long distance = duration * 0.034 / 2;
  
  // 측정 실패 시 999 반환하여 전진 방해 방지
  return (distance == 0) ? 999 : distance;
}

/**
 * @brief 수신된 시리얼 명령에 따라 모터 동작 실행
 */
void executeCommand(char cmd) {
  switch (cmd) {
    case 'F': moveForward();  break;
    case 'B': moveBackward(); break;
    case 'L': turnLeft();     break;
    case 'R': turnRight();    break;
    case 'S': stopMotors();    break;
  }
}

void moveForward() {
  analogWrite(MOTOR_A_IA, MOTOR_VAL);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, MOTOR_VAL);
  analogWrite(MOTOR_B_IB, 0);
}

void moveBackward() {
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, MOTOR_VAL);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, MOTOR_VAL);
}

void turnLeft() {
  analogWrite(MOTOR_A_IA, MOTOR_VAL);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, MOTOR_VAL);
}

void turnRight() {
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, MOTOR_VAL);
  analogWrite(MOTOR_B_IA, MOTOR_VAL);
  analogWrite(MOTOR_B_IB, 0);
}

void stopMotors() {
  analogWrite(MOTOR_A_IA, 0);
  analogWrite(MOTOR_A_IB, 0);
  analogWrite(MOTOR_B_IA, 0);
  analogWrite(MOTOR_B_IB, 0);
}
