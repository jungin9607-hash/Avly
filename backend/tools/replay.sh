#!/bin/sh
# 저장해 둔 분석 결과를 화면에서 다시 보는 모드 (AI를 부르지 않아 비용 0원).
#   sh backend/tools/replay.sh 주차장5     # 그 영상의 저장된 결과를 재생한다 (어떤 영상을 올려도 이 결과가 나온다)
#   sh backend/tools/replay.sh real        # 다시 실제 분석으로 돌아온다
cd "$(dirname "$0")/../.." || exit 1
if [ "$1" = "real" ] || [ -z "$1" ]; then
  ENGINE=avly REDACTION=yolo INSTALL_YOLO=true docker compose up -d worker
else
  ENGINE=replay REDACTION=dev_copy REPLAY_DIR=/app/labels/_replay REPLAY_FIXTURE="$1" docker compose up -d worker
fi
