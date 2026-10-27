-- 판례와 내 사고를 AI 가 비교한 결과를 저장해 두는 곳(캐시).
-- 같은 판례, 같은 사고 상황, 같은 프롬프트·모델이면 AI 를 다시 부르지 않고 같은 설명을 보여 준다.
CREATE TABLE case_ai
(
    cache_key       CHAR(64)        NOT NULL,   -- sha256(판례 본문 + 사고 상황 + 프롬프트 버전 + 모델)
    case_id         UUID            NOT NULL,
    model           VARCHAR(60)     NOT NULL,
    prompt_version  VARCHAR(40)     NOT NULL,
    payload         JSONB           NOT NULL,   -- 검증을 통과한 비교 결과
    input_tokens    INTEGER         NULL,
    output_tokens   INTEGER         NULL,
    created_at      TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_case_ai PRIMARY KEY (cache_key),
    CONSTRAINT fk_case_ai_case FOREIGN KEY (case_id) REFERENCES legal_case (id) ON DELETE CASCADE ON UPDATE RESTRICT
);

COMMENT ON TABLE case_ai IS '판례 비교 AI 결과 캐시';
CREATE INDEX idx_case_ai_case ON case_ai (case_id);
