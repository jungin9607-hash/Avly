"""분석 엔진. worker 가 영상 분석(analyze)을 맡길 때 쓴다.

- avly   : 실제 분석 (OpenAI 키 필요). backend/model/avly 의 파이프라인을 그대로 실행한다.
- replay : 저장해 둔 모델 결과(tests/fixtures)를 재생한다. AI 호출 없이 실제 변환·계산 코드를 시험할 때 쓴다.
- fake   : replay + 영상 첫 줄의 지시로 지원하지 않는 사고·실패 같은 경우를 만들어 낸다. 개발용.

엔진은 analyze(video_path, report) -> (snapshot, stage_logs) 하나만 구현한다.
report(stage_id) 는 진행 단계가 바뀔 때 부른다. 지원하지 않는 사고는 UnsupportedAccident, 너무 긴 영상은 VideoTooLong 을 던진다.
"""

import json
import logging
import os
import time
from pathlib import Path

from app.config import BASE_DIR, settings
from app.worker import snapshot as snap

logger = logging.getLogger(__name__)


class EngineNotConfigured(RuntimeError):
    """AI 키가 없는 것처럼 엔진을 쓸 준비가 안 됐다."""


def _scope():
    from avly import scope   # 가벼운 모듈 (예외와 범위 확인)
    return scope


class ReplayEngine:
    name = "replay"

    def __init__(self, fixture: str | None = None, directory: Path | None = None):
        self.directory = Path(directory or settings.replay_dir)
        self.fixture = fixture or os.environ.get("REPLAY_FIXTURE", "lane_change")

    def _load(self, name: str) -> dict:
        path = self.directory / f"model_result_{name}.json"
        if not path.is_file():
            raise EngineNotConfigured(f"재생할 결과 파일이 없습니다: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def analyze(self, video_path, report):
        scope = _scope()
        data = self._load(self.fixture)
        report("overview")
        snapshot = snap.from_model_result(data, self.name)
        if snapshot["accident_object"] not in scope.SUPPORTED_ACCIDENT_OBJECTS and snapshot["accident_object"] is not None:
            raise scope.UnsupportedAccident(snapshot["accident_object"])
        report("case_matching")
        return snapshot, snap.stage_logs(data)


class FakeEngine(ReplayEngine):
    """영상 첫 줄이 'FAKE ...' 이면 그 지시를 따른다. 그 외에는 replay 와 같다.

    FAKE unsupported 차대보행자  → 지원하지 않는 사고
    FAKE too_long 42.5           → 영상이 너무 김
    FAKE fail                    → 분석 실패
    FAKE fixture parking         → 다른 재생 파일 사용
    """
    name = "fake"

    def __init__(self, delay: float | None = None, **kw):
        super().__init__(**kw)
        self.delay = float(os.environ.get("FAKE_STAGE_DELAY", "0")) if delay is None else delay

    @staticmethod
    def _directive(video_path) -> list[str]:
        with open(video_path, "rb") as f:
            head = f.readline(200).decode("utf-8", "ignore").strip()
        return head.split() if head.startswith("FAKE") else []

    def analyze(self, video_path, report):
        scope = _scope()
        words = self._directive(video_path)
        for stage in ("overview", "detail_review"):
            report(stage)
            time.sleep(self.delay)
        if words[1:2] == ["unsupported"]:
            raise scope.UnsupportedAccident(words[2] if len(words) > 2 else "차대보행자")
        if words[1:2] == ["too_long"]:
            raise scope.VideoTooLong(float(words[2]) if len(words) > 2 else 60.0)
        if words[1:2] == ["fail"]:
            raise RuntimeError("FAKE 지시로 만든 실패")
        if words[1:2] == ["fixture"] and len(words) > 2:
            self.fixture = words[2]
        return super().analyze(video_path, report)


class AvlyEngine:
    name = "avly"

    STAGE_BY_PREFIX = (("2/3", "detail_review"), ("사고 전 차선", "detail_review"), ("3/3", "case_matching"))

    def __init__(self, results_dir: Path | None = None):
        self.results_dir = Path(results_dir or settings.upload_dir / "_model_results")

    def analyze(self, video_path, report):
        # 무거운 의존성(cv2, openai 등)은 실제로 쓸 때만 불러온다
        from avly import observation, pipeline
        from avly.context import ctx

        if not (os.environ.get("OPENAI_API_KEY") or "").strip():
            # 같은 영상을 이미 분석한 응답 캐시가 있으면 키 없이도 되지만, 새 영상은 반드시 필요하다. 미리 알려 준다.
            logger.warning("OPENAI_API_KEY 가 없습니다. 새 AI 요청이 필요하면 실패합니다.")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        def stage_for(name: str):
            return next((sid for prefix, sid in self.STAGE_BY_PREFIX if name.startswith(prefix)), None)

        originals = {m: m.call for m in (pipeline, observation)}

        def wrap(original):
            def call(stage, *args, **kwargs):
                sid = stage_for(stage)
                if sid:
                    report(sid)
                return original(stage, *args, **kwargs)
            return call

        report("overview")
        for module, original in originals.items():
            module.call = wrap(original)
        try:
            pipeline.run({
                "BACKEND_DIR": str(BASE_DIR), "VIDEO_FILE": str(video_path), "PICK_VIDEO": False,
                "CSV_FILE": str(settings.fault_table_path), "RESULTS_DIR": str(self.results_dir),
                "SHOW_PROCESS_LOGS": False, "USE_CACHE": True, "no_survey": True,
            })
            data = json.loads(Path(ctx.output_path).read_text(encoding="utf-8"))
        finally:
            for module, original in originals.items():
                module.call = original
        return snap.from_model_result(data, self.name), snap.stage_logs(data)


def make_engine(name: str | None = None):
    name = (name or settings.engine).lower()
    engines = {"avly": AvlyEngine, "replay": ReplayEngine, "fake": FakeEngine}
    if name not in engines:
        raise ValueError(f"알 수 없는 ENGINE 입니다: {name} (avly, replay, fake 중 하나)")
    return engines[name]()
