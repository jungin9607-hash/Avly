"""서비스 범위: 지금은 차대차 사고만 지원한다.

보행자, 이륜차, 자전거 사고는 과실표(fault_table_car_to_car.csv)에 없으므로 분석하지 않는다.
영상 분석 1단계에서 모델이 사고 대상을 명확히 다른 유형으로 판단하면 이후 단계(AI 호출)를 실행하지 않고 멈춘다.
"""
from .constants import SUPPORTED_ACCIDENT_OBJECTS


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
