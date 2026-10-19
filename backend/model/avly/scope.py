"""서비스 범위: 지금은 차대차 사고만, 사고 전후 15초 내외 영상 하나만 지원한다.

보행자, 이륜차, 자전거 사고는 과실표(fault_table_car_to_car.csv)에 없으므로 분석하지 않는다.
영상 분석 1단계에서 모델이 사고 대상을 명확히 다른 유형으로 판단하면 이후 단계(AI 호출)를 실행하지 않고 멈춘다.
"""
from .constants import MAX_VIDEO_SECONDS, SUPPORTED_ACCIDENT_OBJECTS


class UnsupportedAccident(Exception):
    """지원하지 않는 사고 유형. API 에서는 분석 상태 unsupported 로 바꿔 알린다."""

    def __init__(self, accident_object):
        super().__init__('%s 사고는 지원하지 않습니다. 현재는 차대차 사고만 분석합니다.' % accident_object)
        self.accident_object = accident_object


def check_supported(observation):
    """모델이 사고 대상을 지원 범위 밖으로 판단했을 때만 멈춘다. 비어 있거나 불확실하면(None) 계속 진행한다."""
    obj = observation.accident_object
    if obj is not None and obj not in SUPPORTED_ACCIDENT_OBJECTS:
        raise UnsupportedAccident(obj)


class VideoTooLong(Exception):
    """영상이 너무 김. 사고 전후 15초 내외 영상만 분석한다. API 에서는 분석 실패(VIDEO_TOO_LONG)로 알린다."""

    def __init__(self, seconds):
        super().__init__('영상이 너무 깁니다(%.1f초). 사고 전후 15초 내외(최대 %g초) 영상만 분석할 수 있습니다.' % (seconds, MAX_VIDEO_SECONDS))
        self.seconds = seconds


def check_duration(seconds):
    """AI 를 호출하기 전에 영상 길이를 확인한다."""
    if seconds > MAX_VIDEO_SECONDS:
        raise VideoTooLong(seconds)
