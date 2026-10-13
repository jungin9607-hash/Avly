-- Avly v0.3 PostgreSQL schema (quiz 제외)
-- 테이블 순서는 FK 관계를 고려해 한 번에 실행해도 에러가 나지 않게 정렬됨
-- 필요: pgvector 확장 (Docker 이미지 pgvector/pgvector:pg17)

CREATE EXTENSION IF NOT EXISTS vector;


-- =========================================================
-- accident : 사고
-- =========================================================
CREATE TABLE accident
(
    id            UUID            NOT NULL,
    title         VARCHAR(200)    NOT NULL, --길이가 바뀌는 문자열(최대200자), NOT NULL : 비워둘 수 없다.
    status        VARCHAR(20)     DEFAULT 'uploaded' NOT NULL, --처리 상태, 값을 안 넣으면 자동으로 업로드
    created_at    TIMESTAMPTZ     DEFAULT now() NOT NULL, --사용자가 업로드한 시각, 날짜와 시각을 시간대 정보와 함께 저장(TZ = Time Zone). 서버가 미국에 있어도 한국 시각으로 정확히 바꿔 보여줌
    CONSTRAINT pk_accident PRIMARY KEY (id), --constraint 이름 형태 : 제약조건, id를 기본키로 정함 (중복불가, 빈칸불가)
    CONSTRAINT ck_accident_status CHECK (status IN ('uploaded', 'analyzing', 'completed', 'failed')) --status에는 괄호 안의 4개 값만 들어갈 수 있다.
);

COMMENT ON TABLE  accident            IS '사고';
COMMENT ON COLUMN accident.id         IS '사고 식별자';
COMMENT ON COLUMN accident.title      IS '사고 제목';
COMMENT ON COLUMN accident.status     IS '처리 상태 (uploaded/analyzing/completed/failed)';
COMMENT ON COLUMN accident.created_at IS '등록 시각';


-- =========================================================
-- analysis : 분석
-- =========================================================
CREATE TABLE analysis
(
    id             UUID            NOT NULL,
    accident_id    UUID            NOT NULL, --어떤 사고의 분석인지 적는 칸, accident 테이블의 id 값이 그대로 들어간다.
    fault_me       NUMERIC(5,2)    NOT NULL, --NUMERIC(전체 자릿수, 소수점 아래 자릿수)
    fault_other    NUMERIC(5,2)    NOT NULL,
    confidence     NUMERIC(4,3)    NULL, --AI 모델이 이 결과를 얼마나 확신하는지
    summary        TEXT            NOT NULL, --분석 요약과 판단 근거, 길이 제한이 없는 문자열
    created_at     TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_analysis PRIMARY KEY (id),
    CONSTRAINT ck_analysis_fault_me    CHECK (fault_me BETWEEN 0 AND 100),
    CONSTRAINT ck_analysis_fault_other CHECK (fault_other BETWEEN 0 AND 100),
    CONSTRAINT ck_analysis_fault_sum   CHECK (fault_me + fault_other = 100),
    CONSTRAINT ck_analysis_confidence  CHECK (confidence BETWEEN 0 AND 1)
);

COMMENT ON TABLE  analysis             IS '분석';
COMMENT ON COLUMN analysis.id          IS '분석 식별자';
COMMENT ON COLUMN analysis.accident_id IS '사고 식별자';
COMMENT ON COLUMN analysis.fault_me    IS '본인 과실 (0~100)';
COMMENT ON COLUMN analysis.fault_other IS '상대 과실 (0~100)';
COMMENT ON COLUMN analysis.confidence  IS '모델 신뢰도 (0~1)';
COMMENT ON COLUMN analysis.summary     IS '분석 요약';
COMMENT ON COLUMN analysis.created_at  IS '분석 완료 시각';

ALTER TABLE analysis
    ADD CONSTRAINT fk_analysis_accident FOREIGN KEY (accident_id) --accident 테이블에 실제로 있는 id만 넣을 수 있다는 규칙, 이게 ERD에서 accident와 analysis를 잇는 선
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT; --사고를 지우면 그 사고의 분석 결과도 자동으로 같이 지워짐


-- =========================================================
-- legal_case : 판례
-- =========================================================
CREATE TABLE legal_case
(
    id             UUID            NOT NULL,
    title          VARCHAR(300)    NOT NULL,
    summary        TEXT            NOT NULL,
    fault_ratio    VARCHAR(30)     NULL,
    embedding      VECTOR(1536)    NULL, --*모델에 맞게 숫자 바꾸기* 컴퓨터는 글의 "의미"를 직접 비교하지 못함,. 그래서 임베딩 모델이 판례 요약을 숫자 목록으로 바꿔 주고 이를 비교(RAG) 
    source_url     TEXT            NULL,
    created_at     TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_legal_case PRIMARY KEY (id)
);

COMMENT ON TABLE  legal_case             IS '판례';
COMMENT ON COLUMN legal_case.id          IS '판례 식별자';
COMMENT ON COLUMN legal_case.title       IS '판례 제목';
COMMENT ON COLUMN legal_case.summary     IS '판례 요약';
COMMENT ON COLUMN legal_case.fault_ratio IS '과실비율 (원문 당사자 순서, 예 30:70)';
COMMENT ON COLUMN legal_case.embedding   IS '임베딩 (차원은 임베딩 모델에 맞게 변경)';
COMMENT ON COLUMN legal_case.source_url  IS '원문 출처';
COMMENT ON COLUMN legal_case.created_at  IS '등록 시각';


-- =========================================================
-- video : 영상
-- =========================================================
CREATE TABLE video --(영상 파일은 객체 저장소에 두고 DB는 파일 위치만 저장)
(
    id             UUID             NOT NULL,
    accident_id    UUID             NOT NULL,
    video_url      TEXT             NOT NULL, --영상 파일 위치 EX) videos/3f2b.../front.mp4
    thumbnail      TEXT             NULL, -- *필요한가?* 미리보기 이미지 위치
    duration       NUMERIC(10,3)    NOT NULL, --영상 길이 
    created_at     TIMESTAMPTZ      DEFAULT now() NOT NULL,
    CONSTRAINT pk_video PRIMARY KEY (id),
    CONSTRAINT ck_video_duration CHECK (duration > 0) 영상 길이가 0초 이하면 영상을 저장을 못하게 막음
);

COMMENT ON TABLE  video             IS '영상';
COMMENT ON COLUMN video.id          IS '영상 식별자';
COMMENT ON COLUMN video.accident_id IS '사고 식별자';
COMMENT ON COLUMN video.video_url   IS '영상 경로 (객체 키)'; --객체 키 : 일정시간이 지나면 만료되는 임시 링크
COMMENT ON COLUMN video.thumbnail   IS '썸네일 경로';
COMMENT ON COLUMN video.duration    IS '영상 길이(초)';
COMMENT ON COLUMN video.created_at  IS '업로드 시각';

ALTER TABLE video --이미 만든 VIDEO 테이블을 수정
    ADD CONSTRAINT fk_video_accident FOREIGN KEY (accident_id) --FK 규칙 : 다른 테이블에 실제로 있는 값만 적을 수 있다.
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT; --사고를 지우면 그 사고의 영상도 자동으로 같이 지워짐, 사고의 ID 바꿀 수 없게 막음


-- =========================================================
-- survey : 설문
-- =========================================================
CREATE TABLE survey --(영상만으로 알 수 없는 부분) 설문 데이터를 저장하는 테이블
(
    id             UUID           NOT NULL,
    accident_id    UUID           NOT NULL,
    question       TEXT           NOT NULL,
    answer         TEXT           NULL,
    created_at     TIMESTAMPTZ    DEFAULT now() NOT NULL,
    CONSTRAINT pk_survey PRIMARY KEY (id)
);

COMMENT ON TABLE  survey             IS '설문';
COMMENT ON COLUMN survey.id          IS '응답 식별자';
COMMENT ON COLUMN survey.accident_id IS '사고 식별자';
COMMENT ON COLUMN survey.question    IS '질문';
COMMENT ON COLUMN survey.answer      IS '응답 (미응답은 NULL)';
COMMENT ON COLUMN survey.created_at  IS '질문 생성 시각';

ALTER TABLE survey
    ADD CONSTRAINT fk_survey_accident FOREIGN KEY (accident_id)
        REFERENCES accident (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- timeline : 타임라인
-- =========================================================
CREATE TABLE timeline
(
    id             UUID             NOT NULL,
    analysis_id    UUID             NOT NULL,
    time_sec       NUMERIC(10,3)    NOT NULL,
    event          VARCHAR(100)     NOT NULL,
    description    TEXT             NOT NULL,
    image_url      TEXT             NULL,
    CONSTRAINT pk_timeline PRIMARY KEY (id) --그 시점의 영상 장면을 캡처한 이미지 위치
);

COMMENT ON TABLE  timeline             IS '타임라인';
COMMENT ON COLUMN timeline.id          IS '타임라인 식별자';
COMMENT ON COLUMN timeline.analysis_id IS '분석 식별자';
COMMENT ON COLUMN timeline.time_sec    IS '충돌 기준 상대 시각(초), 충돌 전은 음수';
COMMENT ON COLUMN timeline.event       IS '사건 이름';
COMMENT ON COLUMN timeline.description IS '사건 설명';
COMMENT ON COLUMN timeline.image_url   IS '프레임 경로';

ALTER TABLE timeline
    ADD CONSTRAINT fk_timeline_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- report : 리포트
-- =========================================================
CREATE TABLE report
(
    id             UUID           NOT NULL,
    analysis_id    UUID           NOT NULL,
    pdf_url        TEXT           NOT NULL,
    created_at     TIMESTAMPTZ    DEFAULT now() NOT NULL,
    CONSTRAINT pk_report PRIMARY KEY (id)
);

COMMENT ON TABLE  report             IS '리포트';
COMMENT ON COLUMN report.id          IS '리포트 식별자';
COMMENT ON COLUMN report.analysis_id IS '분석 식별자';
COMMENT ON COLUMN report.pdf_url     IS 'PDF 경로 (객체 키)';
COMMENT ON COLUMN report.created_at  IS '생성 시각';

ALTER TABLE report
    ADD CONSTRAINT fk_report_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;


-- =========================================================
-- case_match : 판례 매칭 (analysis N:M legal_case)
-- =========================================================
CREATE TABLE case_match
(
    analysis_id    UUID                NOT NULL,
    case_id        UUID                NOT NULL,
    similarity     DOUBLE PRECISION    NOT NULL,
    CONSTRAINT pk_case_match PRIMARY KEY (analysis_id, case_id),
    CONSTRAINT ck_case_match_similarity CHECK (similarity BETWEEN -1 AND 1)
);

COMMENT ON TABLE  case_match             IS '판례 매칭';
COMMENT ON COLUMN case_match.analysis_id IS '분석 식별자';
COMMENT ON COLUMN case_match.case_id     IS '판례 식별자';
COMMENT ON COLUMN case_match.similarity  IS '코사인 유사도 (-1~1)';

ALTER TABLE case_match
    ADD CONSTRAINT fk_case_match_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE case_match
    ADD CONSTRAINT fk_case_match_legal_case FOREIGN KEY (case_id)
        REFERENCES legal_case (id) ON DELETE RESTRICT ON UPDATE RESTRICT;


-- =========================================================
-- 인덱스 (FK 조회용)
-- =========================================================
CREATE INDEX idx_video_accident_id      ON video (accident_id); --이 사고의 영상 목록
CREATE INDEX idx_survey_accident_id     ON survey (accident_id); --이 사고의 설문 목록
CREATE INDEX idx_analysis_accident_id   ON analysis (accident_id, created_at DESC); --이 사고의 최신 분석 결과
CREATE INDEX idx_timeline_analysis_id   ON timeline (analysis_id, time_sec); --이 분석의 타임라인을 시간순으로
CREATE INDEX idx_report_analysis_id     ON report (analysis_id); --이 분석의 리포트
CREATE INDEX idx_case_match_case_id     ON case_match (case_id); --이 판례가 쓰인 분석들
