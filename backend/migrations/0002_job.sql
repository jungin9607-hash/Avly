-- 작업 대기열: api 가 등록하고 worker 가 하나씩 가져가 처리한다.
CREATE TABLE job
(
    id            BIGINT          GENERATED ALWAYS AS IDENTITY,
    analysis_id   UUID            NOT NULL,
    kind          VARCHAR(12)     NOT NULL,   -- analyze(영상 분석) / finalize(사용자 확인 뒤 결과 계산)
    status        VARCHAR(10)     DEFAULT 'queued' NOT NULL,
    attempts      INTEGER         DEFAULT 0 NOT NULL,
    payload       JSONB           NULL,
    locked_at     TIMESTAMPTZ     NULL,
    finished_at   TIMESTAMPTZ     NULL,
    error         TEXT            NULL,
    created_at    TIMESTAMPTZ     DEFAULT now() NOT NULL,
    CONSTRAINT pk_job PRIMARY KEY (id),
    CONSTRAINT ck_job_kind CHECK (kind IN ('analyze', 'finalize')),
    CONSTRAINT ck_job_status CHECK (status IN ('queued', 'running', 'done', 'failed'))
);

COMMENT ON TABLE  job           IS '작업 대기열';
COMMENT ON COLUMN job.kind      IS 'analyze(영상 분석) / finalize(사용자 확인 뒤 결과 계산)';
COMMENT ON COLUMN job.locked_at IS 'worker 가 가져간 시각. 오래 지난 running 작업은 다시 대기열로 돌린다';

ALTER TABLE job
    ADD CONSTRAINT fk_job_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis (id) ON DELETE CASCADE ON UPDATE RESTRICT;

CREATE INDEX idx_job_queue ON job (id) WHERE status = 'queued';
CREATE INDEX idx_job_analysis ON job (analysis_id);
