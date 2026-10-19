"""영상 읽기와 프레임 추출."""
import base64
import cv2
import json
import math
import numpy as np
from .constants import POST_SECONDS, PRE_SECONDS, REVIEW_HIGH_IMAGES, REVIEW_IMAGES
from .context import ctx


def inspect_video(path):
    reader = cv2.VideoCapture(str(path))
    try:
        if not reader.isOpened():
            raise ValueError('영상 열기 실패: 경로 또는 코덱 확인 필요')
        video_fps = reader.get(cv2.CAP_PROP_FPS)
        reported = reader.get(cv2.CAP_PROP_FRAME_COUNT)
        if not math.isfinite(video_fps) or video_fps <= 0:
            raise ValueError('유효한 FPS를 읽지 못했습니다. 영상 변환 후 다시 시도하세요.')
        decoded = 0
        while True:
            ok, im = reader.read()
            if not ok or im is None:
                break
            decoded += 1
        if decoded == 0:
            raise ValueError('읽을 수 있는 영상 프레임이 없습니다.')
        audit = {'reported_frame_count': reported if math.isfinite(reported) else None, 'decoded_frame_count': decoded, 'count_method': 'sequential_decode_until_first_failure', 'timing_method': 'frame_index_divided_by_reported_fps'}
        if math.isfinite(reported) and reported > 0 and (int(reported) != decoded):
            print(f'[영상 읽기] 표시 {int(reported)}장 / 실제 읽힘 {decoded}장. 읽힌 범위로 분석합니다.')
            print('[영상 읽기 주의] 끝부분 또는 중간 디코딩 실패일 수 있어 전체 파일 무결성을 보장하지 않습니다.')
        return (video_fps, decoded, audit)
    finally:
        reader.release()

def get_frames(indices):
    requested = sorted(set((int(i) for i in indices)))
    if not requested:
        raise ValueError('분석할 프레임이 없습니다.')
    if requested[0] < 0 or requested[-1] >= ctx.frame_count:
        raise ValueError(f'프레임 요청 범위 오류: 0~{ctx.frame_count - 1}, 요청 {requested[0]}~{requested[-1]}')
    frames = []
    reader = cv2.VideoCapture(str(ctx.VIDEO_PATH))
    try:
        if not reader.isOpened():
            raise RuntimeError('영상을 다시 열 수 없습니다.')
        target = iter(requested)
        next_index = next(target, None)
        for i in range(requested[-1] + 1):
            ok, im = reader.read()
            if not ok or im is None:
                raise RuntimeError(f'순차 프레임 읽기 실패: {i}. 파일 변경/코덱/손상을 확인하세요.')
            if i != next_index:
                continue
            h, w = im.shape[:2]
            scale = min(1, 768 / max(h, w))
            if scale < 1:
                im = cv2.resize(im, (round(w * scale), round(h * scale)))
            annotated = im.copy()
            cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 28), (0, 0, 0), -1)
            cv2.putText(annotated, 'LEFT x=0       CENTER x=0.5       RIGHT x=1', (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
            ok, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                raise RuntimeError('JPEG 인코딩 실패')
            frames.append({'id': f'frame_{i:06d}', 'index': i, 'sec': i / ctx.fps, 'image': im, 'url': 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode()})
            next_index = next(target, None)
        return frames
    finally:
        reader.release()

def background_cues(frames):
    cues = []
    for left, right in zip(frames, frames[1:]):
        g0 = cv2.cvtColor(left['image'], cv2.COLOR_BGR2GRAY)
        g1 = cv2.cvtColor(right['image'], cv2.COLOR_BGR2GRAY)
        mask = np.zeros_like(g0)
        h, w = g0.shape
        mask[:int(h * 0.55), int(w * 0.1):int(w * 0.9)] = 255
        p0 = cv2.goodFeaturesToTrack(g0, 80, 0.02, 8, mask=mask)
        if p0 is None or len(p0) < 12:
            continue
        p1, status, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p0, None)
        if p1 is None or status is None:
            continue
        keep = status.ravel() == 1
        if keep.sum() < 12:
            continue
        transform, inliers = cv2.estimateAffinePartial2D(p0[keep], p1[keep], method=cv2.RANSAC)
        if transform is None or inliers is None or int(inliers.sum()) < 10:
            continue
        cues.append([left['id'], right['id'], round(float(transform[0, 2]), 1), round(float(transform[1, 2]), 1), int(inliers.sum())])
    return cues

def image_content(prompt, frames, high_count=0, high_ids=None):
    allowed = [f['id'] for f in frames]
    prompt += '\n이번 이미지의 허용 프레임 ID 목록: ' + json.dumps(allowed) + '\nframe 번호는 원본 인덱스이며 연속 번호가 아니다. 모든 근거와 first/last는 실제 제공 ID만 인용한다. 중간 번호를 추정/보간하지 마라.'
    content = [{'type': 'input_text', 'text': prompt}]
    high_indices = set(range(max(0, (len(frames) - high_count) // 2), max(0, (len(frames) - high_count) // 2) + high_count))
    for n, f in enumerate(frames):
        content += [{'type': 'input_text', 'text': f"{f['id']} / {f['sec']:.2f}초"}, {'type': 'input_image', 'image_url': f['url'], 'detail': 'high' if (f['id'] in high_ids if high_ids is not None else n in high_indices) else 'low'}]
    return content

def display_frames(frames):
    if not ctx.SHOW_FRAMES:
        return
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(math.ceil(len(frames) / 4), 4, squeeze=False, figsize=(16, 3 * math.ceil(len(frames) / 4)))
    for ax in axes.flat:
        ax.axis('off')
    for ax, f in zip(axes.flat, frames):
        ax.imshow(cv2.cvtColor(f['image'], cv2.COLOR_BGR2RGB))
        ax.set_title(f"{f['sec']:.2f}s / {f['id']}", fontsize=9)
    plt.tight_layout()
    plt.show()
    plt.close(fig)

def uniform_pick(items, limit):
    items = list(items)
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[len(items) // 2]]
    return [items[round((len(items) - 1) * n / (limit - 1))] for n in range(limit)]

def plan_review(anchor, context_start=0):
    first = max(0, anchor - round(0.5 * ctx.fps))
    last = min(ctx.frame_count - 1, anchor + round(0.5 * ctx.fps))
    before_start = max(0, anchor - round(PRE_SECONDS * ctx.fps))
    after_end = min(ctx.frame_count - 1, anchor + round(POST_SECONDS * ctx.fps))
    core = uniform_pick(range(first, last + 1), 16)
    before = uniform_pick(range(before_start, first), 18)
    after = uniform_pick(range(last + 1, after_end + 1), 6)
    picked = set(before + core + after)
    for index in uniform_pick(range(before_start, after_end + 1), REVIEW_IMAGES):
        if len(picked) >= REVIEW_IMAGES:
            break
        picked.add(index)
    return sorted(picked)

def review_high_ids_v2154(frames, anchor):
    core = sorted(frames, key=lambda f: abs(f['index'] - anchor))[:REVIEW_HIGH_IMAGES // 2]
    earlier = [f for f in frames if f['index'] < anchor - round(0.5 * ctx.fps)]
    selected = {f['id'] for f in core + uniform_pick(earlier, REVIEW_HIGH_IMAGES - len(core))}
    for frame in sorted(frames, key=lambda f: abs(f['index'] - anchor)):
        if len(selected) >= REVIEW_HIGH_IMAGES:
            break
        selected.add(frame['id'])
    return selected

def review_high_ids(frames, anchor, road_shape=None):
    if road_shape != '직선 도로':
        return review_high_ids_v2154(frames, anchor)
    if not frames:
        return set()
    offsets = [-3.0, -2.2, -1.6, -1.0, -0.6, -0.2, 0, 0.2]
    selected = {min(frames, key=lambda f: abs(f['index'] - (anchor + round(offset * ctx.fps))))['id'] for offset in offsets[:REVIEW_HIGH_IMAGES]}
    for f in sorted(frames, key=lambda f: abs(f['index'] - anchor)):
        if len(selected) >= REVIEW_HIGH_IMAGES:
            break
        selected.add(f['id'])
    return selected
