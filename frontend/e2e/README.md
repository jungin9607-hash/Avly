# 화면 끝까지 확인 (브라우저 E2E)

실제 브라우저로 업로드부터 결과·타임라인·유사 판례까지 눌러 봅니다. 서버(api, worker, DB)와 프론트가 떠 있어야 합니다.

```bash
cd ~/Avly && docker compose up -d --build        # worker 는 기본으로 가짜 엔진(ENGINE=fake)이라 AI 키가 필요 없습니다

# 브라우저가 들어 있는 이미지로 실행 (처음에는 이미지를 내려받는다, 약 3GB)
docker run --rm --network host -v "$PWD/frontend/e2e:/e2e:ro" -v "$PWD/frontend/e2e/shots:/shots" \
  -e SHOTS_DIR=/shots mcr.microsoft.com/playwright:v1.49.1-jammy \
  sh -c "mkdir -p /tmp/pw && cd /tmp/pw && npm init -y >/dev/null && npm i playwright@1.49.1 >/dev/null && cp /e2e/ui-flow.mjs . && node ui-flow.mjs"
```

- 통과하면 `모두 통과`가 나옵니다. 화면 사진(`frontend/e2e/shots/`, git 에는 올리지 않음)으로 모양도 확인하세요.
- 영상 파일 대신 글자가 든 가짜 파일을 올립니다. 영상 첫 줄의 `FAKE unsupported 차대보행자`, `FAKE too_long 55`, `FAKE fail`, `FAKE fixture parking` 같은 지시로 지원하지 않는 사고·긴 영상 등을 만들어 냅니다.
- 실제 AI 분석(ENGINE=avly)에서는 이 스크립트가 쓰는 가짜 영상이 통하지 않습니다. 실제 영상으로 직접 확인하세요.
