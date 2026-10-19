-- Avly v0.4 PostgreSQL schema (초안)
--
-- v0.3 (schema.sql) 에서 바뀐 점은 schema-v0.4-proposal.md 에 이유와 함께 정리했다.
-- 기존 schema.sql 은 그대로 두었다. 팀이 합의하면 이 파일로 교체한다.
--
-- 전제
--  * 서비스 범위: 차대차 사고만 지원한다. 그 외(보행자, 이륜차, 자전거)는 status = 'unsupported'.
--  * 과실표(fault_table_car_to_car.csv)와 가감요소(adjustment_rules.json)는 저장소 파일로 관리하고 DB 에 넣지 않는다.
--    유형 번호(accident_type_id)는 그 파일의 accident_type 값이다.
--  * 판례는 DB 에서 먼저 찾고, 없으면 API 로 가져와 DB 에 저장한다.
--  * pgvector 는 쓰지 않는다. 의미 검색이 필요해지면 그때 별도 마이그레이션으로 추가한다.
--
-- 테이블 순서는 FK 관계를 고려해 한 번에 실행해도 에러가 나지 않게 정렬했다.


-- =========================================================
-- accident : 사고
-- =========================================================
CREATE TABLE accident
(
    id               UUID            NOT NULL,
    title            VARCHAR(200)    NOT NULL,
    status           VARCHAR(20)     DEFAULT 'uploaded' NOT NULL,
    session_id       UUID            NOT NULL, -- 소유 토큰. 로그인이 없으므로 이 값을 아는 사람만 이 사고를 볼 수 있다.
    consent_version  VARCHAR(20)     NULL,     -- 수집 동의 문서 버전
    consent_at       TIMESTAMPTZ     NULL,     -- 분석 동의 시각 (필수 동의. 동의해야 분석을 시작한다)
    retention_consent_at TIMESTAMPTZ NULL,     -- 영상 저장·추가 활용 동의 시각 (선택). NULL 이면 세션이 끝날 때 영상을 삭제한다
    expires_at       TIMESTAMPTZ     NULL,     -- 세션 만료 시각. 지나면 원본 영상을 삭제한다.
    created_at       TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_accident PRIMARY KEY (id),
    CONSTRAINT ck_accident_status CHECK (status IN ('uploaded', 'analyzing', 'completed', 'failed', 'unsupported'))
);

COMMENT ON TABLE  accident                 IS '사고';
COMMENT ON COLUMN accident.id              IS '사고 식별자';
COMMENT ON COLUMN accident.title           IS '사고 제목';
COMMENT ON COLUMN accident.status          IS '처리 상태 (uploaded/analyzing/completed/failed/unsupported)';
COMMENT ON COLUMN accident.session_id      IS '소유 토큰(세션). 요청마다 함께 보내 본인 사고인지 확인한다';
COMMENT ON COLUMN accident.consent_version IS '수집 동의 문서 버전';
COMMENT ON COLUMN accident.consent_at      IS '분석 동의 시각 (필수)';
COMMENT ON COLUMN accident.retention_consent_at IS '영상 저장·추가 활용 동의 시각 (선택). NULL 이면 세션 종료 시 영상 삭제';
COMMENT ON COLUMN accident.expires_at      IS '세션 만료 시각. 지나면 원본 영상 삭제';
COMMENT ON COLUMN accident.created_at      IS '등록 시각';


-- =========================================================
-- video : 영상 (원본과 번호판 비식별본을 같은 테이블에 둔다)
-- =========================================================
CREATE TABLE video
(
    id                    UUID             NOT NULL,
    accident_id           UUID             NOT NULL,
    kind                  VARCHAR(10)      DEFAULT 'original' NOT NULL,
    source_video_id       UUID             NULL,     -- masked 일 때 원본 영상
    storage_key           TEXT             NOT NULL, -- 객체 저장소의 키 (URL 이 아님. 필요할 때 서명 URL 을 만든다)
    sha256                CHAR(64)         NULL,
    size_bytes            BIGINT           NULL,
    duration              NUMERIC(10,3)    NULL,     -- 초. 추출 전에는 NULL
    fps                   NUMERIC(8,3)     NULL,
    width                 INTEGER          NULL,
    height                INTEGER          NULL,
    thumbnail_key         TEXT             NULL,
    redact_frames_total   INTEGER          NULL,     -- 비식별 처리 통계 (masked 에만)
    plate_frames_detected INTEGER          NULL,
    plate_detections      INTEGER          NULL,
    person_frames_detected INTEGER         NULL,
    person_detections     INTEGER          NULL,
    expires_at            TIMESTAMPTZ      NULL,     -- 원본은 세션 만료 시 삭제
    deleted_at            TIMESTAMPTZ      NULL,
    created_at            TIMESTAMPTZ      DEFAULT now() NOT NULL,
    CONSTRAINT pk_video PRIMARY KEY (id),
    CONSTRAINT ck_video_kind CHECK (kind IN ('original', 'masked')),
    CONSTRAINT ck_video_source CHECK (
        (kind = 'original' AND source_video_id IS NULL) OR
        (kind = 'masked'   AND source_video_id IS NOT NULL)
    ),
    CONSTRAINT ck_video_duration CHECK (duration IS NULL OR duration > 0)
);

COMMENT ON TABLE  video                       IS '영상';
COMMENT ON COLUMN video.kind                  IS 'original(원본) / masked(번호판 비식별본). 분석에는 masked 만 쓴다';
COMMENT ON COLUMN video.source_video_id       IS 'masked 영상의 원본 video.id';
COMMENT ON COLUMN video.storage_key           IS '객체 저장소 키 (만료되는 것은 키가 아니라 서명 URL)';
COMMENT ON COLUMN video.sha256                IS '파일 해시. 같은 영상의 분석 캐시 키로 쓴다';
COMMENT ON COLUMN video.redact_frames_total   IS '비식별 처리한 전체 프레임 수';
COMMENT ON COLUMN video.plate_frames_detected IS '번호판이 탐지된 프레임 수 (검은 박스로 가림)';
COMMENT ON COLUMN video.plate_detections      IS '탐지된 번호판 총 개수';
COMMENT ON COLUMN video.person_frames_detected IS '사람이 탐지된 프레임 수 (사람 전체를 블러)';
COMMENT ON COLUMN video.person_detections     IS '탐지된 사람 총 수 (프레임별 합계)';
COMMENT ON COLUMN video.expires_at            IS '삭제 예정 시각 (원본에만 설정)';
COMMENT ON COLUMN video.deleted_at            IS '실제 삭제 시각. 행은 남기고 파일만 지운다';

ALTER TABLE video
    ADD CONSTRAINT fk_video_accident FOREIGN KEY (accident_id)
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE video
    ADD CONSTRAINT fk_video_source FOREIGN KEY (source_video_id)
        REFERENCES video (id) ON DELETE CASCADE ON UPDATE RESTRICT;

-- 영상은 사고마다 하나만 (원본 기준). 비식별을 다시 처리하면 masked 는 여러 개가 될 수 있다.
CREATE UNIQUE INDEX uq_video_original ON video (accident_id) WHERE kind = 'original';


-- =========================================================
-- analysis : 분석 (작업 상태와 결과를 한 행에 둔다)
-- =========================================================
CREATE TABLE analysis
(
    id                  UUID            NOT NULL,
    accident_id         UUID            NOT NULL,
    video_id            UUID            NOT NULL, -- 분석에 쓴 영상 (번호판 비식별본)
    status              VARCHAR(24)     DEFAULT 'queued' NOT NULL,
    stage               VARCHAR(24)     NULL,     -- processing 일 때 현재 단계
    attempt             INTEGER         DEFAULT 1 NOT NULL,
    parent_analysis_id  UUID            NULL,     -- 재분석이면 이전 분석
    error_code          VARCHAR(40)     NULL,
    error_message       TEXT            NULL,
    unsupported_reason  TEXT            NULL,     -- 예: '차대보행자 사고는 지원하지 않습니다'
    accident_type_id    INTEGER         NULL,     -- 사용자가 확정한 과실표 유형 번호
    fault_me            NUMERIC(5,2)    NULL,     -- 확정하지 못하면 NULL
    fault_other         NUMERIC(5,2)    NULL,
    scene               JSONB           NULL,     -- 1차 분석 중간 결과 (사용자 확인과 재계산에 필요)
    confirmed           JSONB           NULL,     -- 사용자가 확인한 사고 장소, 유형, A 과정, B 과정
    result              JSONB           NULL,     -- 화면에 보여줄 결과 (과실 후보, 가감요소, 타임라인, 판례, 보고서)
    pipeline_version    VARCHAR(80)     NULL,     -- 어떤 코드로 만든 결과인지
    video_sha256        CHAR(64)        NULL,
    csv_sha256          CHAR(64)        NULL,     -- 어떤 과실표로 만든 결과인지
    started_at          TIMESTAMPTZ     NULL,
    finished_at         TIMESTAMPTZ     NULL,
    created_at          TIMESTAMPTZ     DEFAULT now() NOT NULL,
    updated_at          TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_analysis PRIMARY KEY (id),
    CONSTRAINT ck_analysis_status CHECK (status IN
        ('queued', 'processing', 'awaiting_confirmation', 'completed', 'failed', 'unsupported')),
    CONSTRAINT ck_analysis_stage CHECK (stage IS NULL OR stage IN
        ('plate_masking', 'overview', 'detail_review', 'case_matching')),
    CONSTRAINT ck_analysis_fault_range CHECK (
        (fault_me    IS NULL OR fault_me    BETWEEN 0 AND 100) AND
        (fault_other IS NULL OR fault_other BETWEEN 0 AND 100)),
    -- 과실은 둘 다 없거나(확정 못 함), 둘 다 있고 합이 100
    CONSTRAINT ck_analysis_fault_pair CHECK (
        (fault_me IS NULL AND fault_other IS NULL) OR
        (fault_me IS NOT NULL AND fault_other IS NOT NULL AND fault_me + fault_other = 100)),
    CONSTRAINT ck_analysis_completed_has_result CHECK (status <> 'completed' OR result IS NOT NULL),
    CONSTRAINT ck_analysis_failed_has_error CHECK (status <> 'failed' OR error_code IS NOT NULL),
    CONSTRAINT ck_analysis_attempt CHECK (attempt >= 1)
);

COMMENT ON TABLE  analysis                    IS '분석 (상태와 결과)';
COMMENT ON COLUMN analysis.video_id           IS '분석에 쓴 영상. 번호판 비식별본(kind=masked)만 가리킨다';
COMMENT ON COLUMN analysis.status             IS 'queued/processing/awaiting_confirmation/completed/failed/unsupported';
COMMENT ON COLUMN analysis.stage              IS '진행 단계 (plate_masking/overview/detail_review/case_matching)';
COMMENT ON COLUMN analysis.parent_analysis_id IS '재분석이면 이전 분석 id';
COMMENT ON COLUMN analysis.unsupported_reason IS '지원하지 않는 사고 유형일 때 이유 (예: 차대보행자)';
COMMENT ON COLUMN analysis.accident_type_id   IS '확정된 과실표 유형 번호 (fault_table_car_to_car.csv 의 accident_type)';
COMMENT ON COLUMN analysis.fault_me           IS '내 과실. 확정 못 하면 NULL (fault_other 도 NULL)';
COMMENT ON COLUMN analysis.scene              IS '1차 분석 중간 결과 JSON';
COMMENT ON COLUMN analysis.confirmed          IS '사용자가 확인한 4개 항목(사고 장소/유형/A 과정/B 과정) JSON';
COMMENT ON COLUMN analysis.result             IS '결과 JSON. fault_options, timeline, related_cases, report_text 포함';
COMMENT ON COLUMN analysis.pipeline_version   IS '분석 코드 버전 (재현용)';
COMMENT ON COLUMN analysis.csv_sha256         IS '분석에 쓴 과실표 파일 해시 (재현용)';

ALTER TABLE analysis
    ADD CONSTRAINT fk_analysis_accident FOREIGN KEY (accident_id)
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE analysis
    ADD CONSTRAINT fk_analysis_video FOREIGN KEY (video_id)
        REFERENCES video (id) ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE analysis
    ADD CONSTRAINT fk_analysis_parent FOREIGN KEY (parent_analysis_id)
        REFERENCES analysis (id) ON DELETE SET NULL ON UPDATE RESTRICT;

-- 사고 하나에 진행 중인 분석은 하나만 (v0.3 에서는 서버 메모리에서만 검사했다)
CREATE UNIQUE INDEX uq_analysis_active ON analysis (accident_id)
    WHERE status IN ('queued', 'processing', 'awaiting_confirmation');


-- =========================================================
-- survey : 설문 (사전 질문, 모델이 만든 추가 질문, 가감요소 질문)
-- =========================================================
CREATE TABLE survey
(
    id             UUID            NOT NULL,
    accident_id    UUID            NOT NULL,
    analysis_id    UUID            NULL,     -- 사전 설문은 NULL, 추가/가감 질문은 해당 분석
    kind           VARCHAR(12)     NOT NULL,
    key            VARCHAR(60)     NOT NULL, -- 질문 식별자 (예: signal, b_action)
    group_name     VARCHAR(60)     NULL,
    question       TEXT            NOT NULL,
    options        JSONB           NULL,     -- 선택지 목록
    answer         TEXT            NULL,     -- 미응답은 NULL
    answered_at    TIMESTAMPTZ     NULL,
    created_at     TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_survey PRIMARY KEY (id),
    CONSTRAINT ck_survey_kind CHECK (kind IN ('pre', 'follow_up', 'adjustment')),
    CONSTRAINT ck_survey_scope CHECK (
        (kind = 'pre' AND analysis_id IS NULL) OR
        (kind <> 'pre' AND analysis_id IS NOT NULL))
);

COMMENT ON TABLE  survey             IS '설문';
COMMENT ON COLUMN survey.analysis_id IS '이 질문이 속한 분석. 사전 설문(kind=pre)은 NULL';
COMMENT ON COLUMN survey.kind        IS 'pre(분석 전 고정 질문) / follow_up(모델이 만든 추가 질문) / adjustment(가감요소 질문)';
COMMENT ON COLUMN survey.key         IS '질문 식별자';
COMMENT ON COLUMN survey.options     IS '선택지 JSON 배열';
COMMENT ON COLUMN survey.answer      IS '응답 (미응답은 NULL)';

ALTER TABLE survey
    ADD CONSTRAINT fk_survey_accident FOREIGN KEY (accident_id)
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE survey
    ADD CONSTRAINT fk_survey_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;

-- 같은 질문은 한 번만 (사전 설문은 사고 기준, 나머지는 분석 기준)
CREATE UNIQUE INDEX uq_survey_pre      ON survey (accident_id, key) WHERE analysis_id IS NULL;
CREATE UNIQUE INDEX uq_survey_analysis ON survey (analysis_id, kind, key) WHERE analysis_id IS NOT NULL;


-- =========================================================
-- analysis_stage_log : 분석 단계별 호출 기록 (비용, 속도, 모델 비교용)
-- =========================================================
CREATE TABLE analysis_stage_log
(
    id             BIGINT          GENERATED ALWAYS AS IDENTITY,
    analysis_id    UUID            NOT NULL,
    stage          VARCHAR(40)     NOT NULL, -- 단계 이름 (예: 1/3 전체 흐름 분석)
    provider       VARCHAR(20)     NULL,     -- openai / gemini ...
    model          VARCHAR(60)     NULL,
    input_tokens   INTEGER         NULL,
    output_tokens  INTEGER         NULL,
    cached         BOOLEAN         DEFAULT FALSE NOT NULL,
    latency_ms     INTEGER         NULL,
    status         VARCHAR(10)     DEFAULT 'ok' NOT NULL,
    created_at     TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_analysis_stage_log PRIMARY KEY (id),
    CONSTRAINT ck_analysis_stage_log_status CHECK (status IN ('ok', 'error', 'retry'))
);

COMMENT ON TABLE  analysis_stage_log              IS '분석 단계별 AI 호출 기록';
COMMENT ON COLUMN analysis_stage_log.cached       IS '캐시된 응답을 썼으면 true (이때는 토큰이 NULL)';
COMMENT ON COLUMN analysis_stage_log.latency_ms   IS '호출에 걸린 시간(ms)';

ALTER TABLE analysis_stage_log
    ADD CONSTRAINT fk_analysis_stage_log_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- legal_case : 판례 (DB 에서 먼저 찾고, 없으면 API 로 가져와 저장)
-- =========================================================
CREATE TABLE legal_case
(
    id             UUID            NOT NULL,
    court          VARCHAR(100)    NOT NULL,
    decided_on     DATE            NULL,
    case_number    VARCHAR(60)     NOT NULL,
    title          VARCHAR(300)    NULL,
    summary        TEXT            NOT NULL,
    fault_ratio    VARCHAR(30)     NULL,     -- 판례에 소개된 비율 (원문 표기)
    source_kind    VARCHAR(20)     NOT NULL,
    source_url     TEXT            NULL,
    verified       BOOLEAN         DEFAULT FALSE NOT NULL, -- 사람이 검수했는가
    verified_by    VARCHAR(60)     NULL,
    verified_at    TIMESTAMPTZ     NULL,
    raw            JSONB           NULL,     -- API 원본 응답 (감사용)
    fetched_at     TIMESTAMPTZ     NULL,     -- API 로 가져온 시각
    created_at     TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_legal_case PRIMARY KEY (id),
    CONSTRAINT uq_legal_case_number UNIQUE (court, case_number),
    CONSTRAINT ck_legal_case_source CHECK (source_kind IN ('knia_chart', 'law_api', 'manual')),
    CONSTRAINT ck_legal_case_verified CHECK (NOT verified OR verified_at IS NOT NULL)
);

COMMENT ON TABLE  legal_case             IS '판례';
COMMENT ON COLUMN legal_case.source_kind IS 'knia_chart(손해보험협회 도표의 요약) / law_api(법령 API) / manual(직접 입력)';
COMMENT ON COLUMN legal_case.verified    IS '검수 여부. API 로 가져온 판례는 false 로 시작하고, 화면에 "검수 전"으로 표시한다';
COMMENT ON COLUMN legal_case.raw         IS 'API 원본 응답. 요약이 잘못됐을 때 원문을 확인하는 용도';


-- =========================================================
-- case_accident_type : 판례 <-> 과실표 유형 (N:M)
-- =========================================================
CREATE TABLE case_accident_type
(
    accident_type_id  INTEGER         NOT NULL,
    case_id           UUID            NOT NULL,
    relevance_status  VARCHAR(40)     DEFAULT 'registered_chart_reference' NOT NULL,
    comparison_limit  TEXT            NULL,   -- "이 판례를 현재 사고에 그대로 적용하면 안 되는 이유"
    CONSTRAINT pk_case_accident_type PRIMARY KEY (accident_type_id, case_id)
);

COMMENT ON TABLE  case_accident_type                  IS '판례와 과실표 유형 연결';
COMMENT ON COLUMN case_accident_type.accident_type_id IS '과실표 유형 번호 (fault_table_car_to_car.csv 의 accident_type)';
COMMENT ON COLUMN case_accident_type.comparison_limit IS '비교 한계 문구. 사용자가 판례 비율을 그대로 적용하지 않게 하는 안내';

ALTER TABLE case_accident_type
    ADD CONSTRAINT fk_case_accident_type_case FOREIGN KEY (case_id)
        REFERENCES legal_case (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- case_lookup : 유형별 판례 조회 기록 (판례가 없는 유형에서 API 를 반복 호출하지 않기 위함)
-- =========================================================
CREATE TABLE case_lookup
(
    accident_type_id  INTEGER         NOT NULL,
    status            VARCHAR(10)     NOT NULL,
    case_count        INTEGER         DEFAULT 0 NOT NULL,
    looked_up_at      TIMESTAMPTZ     DEFAULT now() NOT NULL,
    retry_after       TIMESTAMPTZ     NULL,   -- 이 시각 전에는 API 를 다시 부르지 않는다
    CONSTRAINT pk_case_lookup PRIMARY KEY (accident_type_id),
    CONSTRAINT ck_case_lookup_status CHECK (status IN ('found', 'empty', 'error'))
);

COMMENT ON TABLE  case_lookup              IS '유형별 판례 API 조회 기록';
COMMENT ON COLUMN case_lookup.status       IS 'found(찾음) / empty(결과 없음) / error(API 오류)';
COMMENT ON COLUMN case_lookup.retry_after  IS '다음 조회 가능 시각 (empty, error 일 때 간격을 둔다)';


-- =========================================================
-- report : 리포트 (PDF)
-- =========================================================
CREATE TABLE report
(
    id             UUID           NOT NULL,
    analysis_id    UUID           NOT NULL,
    pdf_key        TEXT           NOT NULL, -- 객체 저장소 키
    created_at     TIMESTAMPTZ    DEFAULT now() NOT NULL,
    CONSTRAINT pk_report PRIMARY KEY (id)
);

COMMENT ON TABLE  report         IS '리포트';
COMMENT ON COLUMN report.pdf_key IS 'PDF 객체 저장소 키';

ALTER TABLE report
    ADD CONSTRAINT fk_report_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- 인덱스
-- =========================================================
CREATE INDEX idx_accident_session         ON accident (session_id, created_at DESC); -- 내 사고 목록
CREATE INDEX idx_accident_expires         ON accident (expires_at) WHERE expires_at IS NOT NULL; -- 만료 정리 작업
CREATE INDEX idx_video_accident_id        ON video (accident_id);
CREATE INDEX idx_video_expires            ON video (expires_at) WHERE expires_at IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_analysis_accident_id     ON analysis (accident_id, created_at DESC); -- 이 사고의 최신 분석
CREATE INDEX idx_survey_accident_id       ON survey (accident_id);
CREATE INDEX idx_stage_log_analysis_id    ON analysis_stage_log (analysis_id);
CREATE INDEX idx_case_accident_type_case  ON case_accident_type (case_id);
CREATE INDEX idx_report_analysis_id       ON report (analysis_id);
