"""Avly license plate redaction prototype. Review outputs before sharing."""
from pathlib import Path
import cv2
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

MODEL_REPO = 'Koushim/yolov8-license-plate-detection'


def mosaic_video(input_path, output_path, confidence=0.25, margin_ratio=0.12):
    """Cover detected license plates with opaque black rectangles.

    Returns basic processing counts. This is not a privacy guarantee.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(f'Input video not found: {input_path}')
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Input and output paths must differ')
    if not 0 < confidence <= 1:
        raise ValueError('confidence must be between 0 and 1')

    model_file = hf_hub_download(repo_id=MODEL_REPO, filename='best.pt')
    model = YOLO(model_file)
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f'Cannot open video: {input_path}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or width <= 0 or height <= 0:
        cap.release()
        raise ValueError('Invalid video properties')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise ValueError(f'Cannot write video: {output_path}')
    frames, frames_with_plates, plate_detections = 0, 0, 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            result = model.predict(source=frame, conf=confidence, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            if len(boxes):
                frames_with_plates += 1
            for x1, y1, x2, y2 in boxes:
                dx = max(5, int((x2 - x1) * margin_ratio))
                dy = max(5, int((y2 - y1) * margin_ratio))
                left = max(0, int(x1) - dx)
                top = max(0, int(y1) - dy)
                right = min(width - 1, int(x2) + dx)
                bottom = min(height - 1, int(y2) + dy)
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 0), -1)
                plate_detections += 1
            writer.write(frame)
            frames += 1
    finally:
        cap.release()
        writer.release()
    if frames == 0:
        output_path.unlink(missing_ok=True)
        raise ValueError('No frames could be read')
    return {'output_path': str(output_path), 'frames': frames,
            'frames_with_plates': frames_with_plates, 'plate_detections': plate_detections}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Cover detected license plates in a video')
    parser.add_argument('input', help='Input video path')
    parser.add_argument('output', help='Output video path')
    args = parser.parse_args()
    print(mosaic_video(args.input, args.output))
