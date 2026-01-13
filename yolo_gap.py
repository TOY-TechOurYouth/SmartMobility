import cv2
import numpy as np
from ultralytics import YOLO

# 웹캠 스트리밍 주소
STREAM_URL = "http://172.20.10.6:8080/?action=stream"

# 아래 띠(ROI) 비율
ROI_TOP_RATIO = 0.6   # 아래 40% 정도를 바닥 띠로 사용
MIN_GAP_PIXELS = 120  # RC카가 지나갈 수 있는 최소 가로 픽셀 폭 (임시값)


def detect_gaps_from_boxes(h, w, boxes):
    """
    h, w : frame 크기
    boxes: YOLO 탐지 결과 bbox list [ (x1,y1,x2,y2), ... ]

    반환: gaps = [(u_start, u_end)], roi_top, roi_bottom, occ
    occ: width 크기의 1D occupancy 배열 (0=빈 공간, 1=장애물)
    """
    # ROI 영역(바닥 띠)
    roi_top = int(h * ROI_TOP_RATIO)
    roi_bottom = h

    # 1D occupancy 라인 (width 길이)
    occ = np.zeros(w, dtype=np.uint8)  # 0: free, 1: blocked

    # 장애물 박스를 occupancy에 반영
    for (x1, y1, x2, y2) in boxes:
        # ROI 띠와 겹치는 박스만 고려
        if y2 < roi_top or y1 > roi_bottom:
            continue

        # ROI와 겹치는 가로 구간만 차단
        u1 = max(0, int(x1))
        u2 = min(w, int(x2))
        occ[u1:u2] = 1  # 이 구간은 장애물

    # 연속된 free 구간(gap) 찾기
    gaps = []
    in_gap = False
    start = 0
    for x in range(w):
        # 빈공간에서 gap 시작
        if occ[x] == 0 and not in_gap:
            in_gap = True
            start = x
        # 장애물 만나거나 마지막 pixel -> gap 종료
        elif (occ[x] == 1 or x == w - 1) and in_gap:
            end = x if occ[x] == 1 else x + 1
            if end - start >= MIN_GAP_PIXELS:
                gaps.append((start, end))
            in_gap = False

    return gaps, roi_top, roi_bottom, occ


def main():
    # detection 전용 YOLO (세그멘테이션 X → 더 빠름)
    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(STREAM_URL)
    print("Stream opened:", cap.isOpened())
    if not cap.isOpened():
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape

        # 해상도 줄여서 속도 올리기 (예: 640 x 360)
        frame_small = cv2.resize(frame, (640, 360))

        # YOLO 탐지 수행 (conf 약간 낮춰서 더 잘 잡히게)
        results = model(frame_small, imgsz=640, conf=0.25, verbose=False)[0]

        # YOLO 결과 좌표를 원본 frame 기준으로 스케일 복원
        scale_x = w / 640
        scale_y = h / 360

        obstacle_boxes = []

        # 클래스 필터링 없이, 탐지된 모든 박스를 장애물 후보로 사용
        for box in results.boxes.xyxy:
            x1, y1, x2, y2 = box.tolist()
            # 원본 좌표로 되돌리기
            x1 *= scale_x
            x2 *= scale_x
            y1 *= scale_y
            y2 *= scale_y
            obstacle_boxes.append((x1, y1, x2, y2))

        # gap 탐지
        gaps, roi_top, roi_bottom, occ = detect_gaps_from_boxes(h, w, obstacle_boxes)

        vis = frame.copy()

        # 1) gap 영역을 초록색으로 칠하기 (ROI 안)
        overlay = vis.copy()
        best_gap = None

        if gaps:
            best_gap = max(gaps, key=lambda g: g[1] - g[0])

            for (u1, u2) in gaps:
                cv2.rectangle(
                    overlay,
                    (u1, roi_top),
                    (u2, roi_bottom),
                    (0, 255, 0),   # 초록색
                    thickness=-1,  # 채우기
                )

        # 투명도 합성
        vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

        # 2) ROI 경계선 표시
        cv2.line(vis, (0, roi_top), (w, roi_top), (0, 255, 255), 2)
        cv2.line(vis, (0, roi_bottom - 1), (w, roi_bottom - 1), (0, 255, 255), 2)

        # 3) 장애물 bbox는 빨간 박스로
        for (x1, y1, x2, y2) in obstacle_boxes:
            cv2.rectangle(
                vis,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 0, 255),
                2,
            )

        # GO/NO-GO 판정
        # 4) 상태 텍스트 & best gap 강조
        status_text = "NO GAP"
        color = (0, 0, 255)
        gap_width = 0

        if best_gap is not None:
            u1, u2 = best_gap
            gap_width = u2 - u1

            # best gap 테두리 강조
            cv2.rectangle(
                vis,
                (u1, roi_top),
                (u2, roi_bottom),
                (0, 255, 0),
                3,
            )

            # gap 넓이가 기준 이상이면 GO
            if gap_width >= MIN_GAP_PIXELS:
                status_text = f"GO  (w={gap_width}px)"
                color = (0, 255, 0)
            else:
                status_text = f"NO-GO  (w={gap_width}px)"
                color = (0, 0, 255)

        cv2.putText(
            vis,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            color,
            2,
            cv2.LINE_AA,
        )

        # 창 출력
        cv2.imshow("RC Car - Fast Box Gap", vis)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
