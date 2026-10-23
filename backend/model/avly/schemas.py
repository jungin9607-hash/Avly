"""모델 응답 형식(Pydantic)."""
from pydantic import BaseModel, Field, PrivateAttr
from typing import Literal
from .constants import Action


class Track(BaseModel):
    vehicle_id: str
    camera_role: Literal['카메라 차량', '외부 차량', '미확인']
    appearance: str
    first_frame_id: str
    last_frame_id: str
    evidence_frame_ids: list[str]
    movement: str
    exit_observation: str

class Phase(BaseModel):
    first_frame_id: str
    last_frame_id: str
    state: Literal['정지 추정', '이동 추정', '판단 불가']
    background_evidence: str

class ScreenPoint(BaseModel):
    frame_id: str
    x_center: float = Field(ge=0, le=1)
    visibility: Literal['차량 중심 식별 가능', '일부만 보임', '동일성 불확실']

class LaneCrossing(BaseModel):
    vehicle: Literal['A', 'B']
    before_frame_id: str
    after_frame_id: str
    visible_lane_boundary: str

class VehicleState(BaseModel):
    motion: Literal['이동', '정지', '미확인']
    roundabout_position: Literal['진입', '내부 회전', '진출', '진입 전 대기', '미확인']
    lane_change: Literal['있음', '없음', '미확인']
    motion_frame_ids: list[str]
    position_frame_ids: list[str]
    lane_change_frame_ids: list[str]

def unknown_state():
    return VehicleState(motion='미확인', roundabout_position='미확인', lane_change='미확인', motion_frame_ids=[], position_frame_ids=[], lane_change_frame_ids=[])

class RouteCheck(BaseModel):
    vehicle: Literal['A', 'B']
    first_frame_id: str | None
    last_frame_id: str | None
    first_position: Literal['진입부 바깥', '회전차로 내부', '진출 도로', '미확인']
    last_position: Literal['진입부 바깥', '회전차로 내부', '진출 도로', '미확인']
    landmark: str
    first_relation: str
    last_relation: str
    conflicting_cues: bool
    alternative_explanation: str

class SignalCheck(BaseModel):
    signal_present: Literal['있음', '없음', '미확인'] = '미확인'
    signal_operating: Literal['정상 작동', '점멸', '꺼짐', '미확인'] = '미확인'
    a_signal: Literal['녹색', '황색', '적색', '미확인'] = '미확인'
    b_signal: Literal['녹색', '황색', '적색', '미확인'] = '미확인'
    evidence_frame_ids: list[str] = Field(default_factory=list)

class SpecialCondition(BaseModel):
    vehicle: Literal['A', 'B']
    condition: Literal['centerline_crossing', 'wrong_way', 'overtaking', 'opposing_travel']
    value: Literal['있음', '없음', '미확인']
    evidence_frame_ids: list[str]
    explanation: str

class ManeuverCheck(BaseModel):
    vehicle: Literal['A', 'B']
    action: Action
    support: Literal['관찰', '추정', '미확인']
    evidence_frame_ids: list[str]
    vehicle_orientation: str
    fixed_background: str
    path_description: str
    alternative_explanation: str

class ParkingRouteCheck(BaseModel):
    origin_visibility: Literal['출발 구역부터 연속 관찰', '통로 진입 후만 관찰', '미확인'] = '미확인'
    boundary_evidence: str = ''
    vehicle: Literal['A', 'B']
    start_zone: Literal['통로', '주차구역', '도로', '미확인']
    end_zone: Literal['통로', '주차구역', '도로', '미확인']
    evidence_frame_ids: list[str]
    explanation: str
    support: Literal['관찰', '추정', '미확인']

class StraightRelationCheck(BaseModel):
    b_vehicle_id: str | None = None
    b_position: Literal['앞', '뒤', '옆', '미확인'] = '미확인'
    same_direction: Literal['같은 방향', '반대 방향', '미확인'] = '미확인'
    b_visible_face: Literal['후면', '전면', '측면', '미확인'] = '미확인'
    moving_before_stop: Literal['있음', '없음', '미확인'] = '미확인'
    mechanism: Literal['추돌', '차로변경 직후 충돌', '합류', '미확인'] = '미확인'
    merge_path_evidence: str = ''
    support: Literal['관찰', '추정', '미확인'] = '미확인'
    evidence_frame_ids: list[str] = Field(default_factory=list)
    explanation: str = ''

class ParkingMotionPhase(BaseModel):
    turn_geometry_evidence: str = ''
    vehicle: Literal['A', 'B']
    action: Action
    first_frame_id: str
    last_frame_id: str
    evidence_frame_ids: list[str]
    support: Literal['관찰', '추정', '미확인']
    vehicle_orientation: str
    fixed_background: str
    explanation: str

class FlowStep(BaseModel):
    stage: Literal['접근', '사고 직전', '접촉', '접촉 이후']
    description: str
    support: Literal['관찰', '추정', '미확인']
    first_frame_id: str
    last_frame_id: str
    evidence_frame_ids: list[str]

class AdjustmentObservation(BaseModel):
    actor: Literal['A', 'B']
    factor: Literal['round_entry_stop', 'round_entry_prior', 'round_entry_signal_delay', 'slow_or_stop', 'wide_right_turn', 'clear_prior_entry', 't_intersection_turn', 'slow_failure', 'opposite_arrow', 'protruding_wait_exit', 'signal_delay', 'prohibited_change', 'bus_lane_violation', 'passing_lane_change', 'gross_negligence', 'serious_negligence', 'low_speed_unjustified_stop', 'unjustified_sudden_stop', 'brake_light_fault', 'residential_area']
    value: Literal['있음', '없음', '미확인']
    support: Literal['관찰', '추정', '미확인']
    evidence_frame_ids: list[str]
    explanation: str

class Observation(BaseModel):
    accident_flow: list[FlowStep] = Field(default_factory=list)
    road_shape_revision_reason: str = ''
    adjustment_observations: list[AdjustmentObservation] = Field(default_factory=list)
    parking_motion_phases: list[ParkingMotionPhase] = Field(default_factory=list)
    straight_relation: StraightRelationCheck = Field(default_factory=StraightRelationCheck)
    _evidence_audit: dict = PrivateAttr(default_factory=dict)
    summary: str
    tracks: list[Track]
    b_vehicle_id: str | None
    b_identity: Literal['구별됨', '혼동 가능', '판단 불가']
    a_phases: list[Phase]
    accident_object: Literal['차대차', '차대보행자', '차대이륜차', '차대자전거'] | None
    road_place_codes: list[int]
    road_evidence: str
    contact: Literal['접촉 관찰', '충돌 정황 강함', '접촉 추정', '근접만 관찰', '판단 불가']
    contact_evidence: str
    contact_frame_ids: list[str]
    impact_anchor_frame_id: str | None
    impact_cues: list[str]
    pre_contact_a_movement: str
    pre_contact_b_movement: str
    pre_contact_evidence_frame_ids: list[str]
    a_action: Action
    b_action: Action
    a_state: VehicleState
    b_state: VehicleState
    roundabout_lane_count: Literal['1차로', '2차로 이상', '미확인']
    lane_count_frame_ids: list[str]
    observation_issues: list[str]
    b_screen_points: list[ScreenPoint]
    a_pre_frame_ids: list[str]
    b_pre_frame_ids: list[str]
    lane_crossings: list[LaneCrossing]
    road_shape: Literal['회전교차로', '직선 도로', '교차로', '주차장', '주차장/기타', '기타', '미확인']
    road_shape_evidence_frame_ids: list[str]
    priority: Literal['높음', '중간', '낮음', '후보 없음']
    review_needed: bool
    review_first_frame_id: str | None
    review_last_frame_id: str | None
    review_reason: str
    unknowns: list[str]
    route_checks: list[RouteCheck] = Field(default_factory=list)
    signal_check: SignalCheck = Field(default_factory=SignalCheck)
    special_conditions: list[SpecialCondition] = Field(default_factory=list)
    maneuver_checks: list[ManeuverCheck] = Field(default_factory=list)
    parking_route_checks: list[ParkingRouteCheck] = Field(default_factory=list)
    camera_view: Literal['전방', '후방', '측방', '미확인'] = '미확인'

class Scan(BaseModel):
    summary: str
    tracks: list[Track]
    a_phases: list[Phase]
    accident_object: Literal['차대차', '차대보행자', '차대이륜차', '차대자전거'] | None
    road_place_codes: list[int]
    road_evidence: str
    contact: Literal['접촉 관찰', '충돌 정황 강함', '접촉 추정', '근접만 관찰', '판단 불가']
    contact_evidence: str
    contact_frame_ids: list[str]
    impact_anchor_frame_id: str | None
    priority: Literal['높음', '중간', '낮음', '후보 없음']
    road_shape: Literal['회전교차로', '직선 도로', '교차로', '주차장', '주차장/기타', '기타', '미확인'] = '미확인'
    road_shape_evidence_frame_ids: list[str] = Field(default_factory=list)
    camera_view: Literal['전방', '후방', '측방', '미확인'] = '미확인'

class Candidate(BaseModel):
    accident_type: int
    dashcam_table_role: Literal['A', 'B', '미확인']
    common_observed_facts: list[str]
    assumed_conditions: list[str]
    a_role_evidence: str
    b_role_evidence: str
    mapped_a_progress: str
    mapped_b_progress: str
    a_evidence_frame_ids: list[str]
    b_evidence_frame_ids: list[str]
    a_condition_status: Literal['관찰됨', '가정', '미확인']
    b_condition_status: Literal['관찰됨', '가정', '미확인']
    reason: str

class Question(BaseModel):
    answer_key: str
    question: str
    options: list[str]

class Matches(BaseModel):
    candidates: list[Candidate]
    survey: list[Question]
    no_match_reason: str

class FrameReferenceError(ValueError):

    def __init__(self, invalid, allowed):
        self.invalid = invalid
        self.allowed = sorted(allowed)
        detail = '; '.join((f"{x['field']}={x['id']}" for x in invalid))
        super().__init__('제공하지 않은 프레임 인용: ' + detail)

    def diagnostic(self):
        return {'invalid_references': self.invalid, 'allowed_frame_ids': self.allowed}

class LaneCauseReview(BaseModel):
    b_vehicle_id: str | None
    lane_change: Literal['있음', '없음', '미확인']
    boundary_type: Literal['실선', '점선', '미확인']
    before_frame_id: str | None
    after_frame_id: str | None
    before_side: Literal['왼쪽', '오른쪽', '경계 위', '미확인']
    after_side: Literal['왼쪽', '오른쪽', '경계 위', '미확인']
    evidence_frame_ids: list[str]
    explanation: str
