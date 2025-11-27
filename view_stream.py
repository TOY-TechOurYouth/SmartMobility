import cv2

STREAM_URL = "http://192.168.45.246:8080/?action=stream"

def main():
    cap = cv2.VideoCapture(STREAM_URL)

    if not cap.isOpened():
        print("❌ 스트림을 열 수 없습니다.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임을 읽을 수 없습니다.")
            break

        cv2.imshow("RC Car Camera (Python 3.13 venv)", frame)

        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
