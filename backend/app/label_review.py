"""사고 유형 쉬운 말(app/data/accident_labels.json)을 검수하기 좋은 표(마크다운)로 출력한다.

    python -m app.label_review > docs/review/accident-labels-review.md
"""

from app import catalog

KINDS = [
    ("places", "사고 장소 (7개)", "place"),
    ("features", "사고 특징 (30개)", "feature"),
    ("progress", "차량 진행 (146개)", "my_progress"),
]


def render() -> str:
    data = catalog.labels()
    lines = [
        "# 사고 유형 쉬운 말 검수표",
        "",
        "사고 상황 확인 화면과 결과 화면에 나가는 사고 유형 이름의 쉬운 말입니다. 과실표(손해보험협회 인정기준)의 원래 이름은 그대로 두고, 화면에 보이는 이름만 바꿉니다.",
        "이 표는 `backend/app/data/accident_labels.json`에서 만든 읽기용입니다. **고칠 때는 JSON 파일을 직접 고칩니다.** (아래 \"검수 방법\")",
        "",
        "## 검수 방법",
        "",
        "1. VS Code에서 `backend/app/data/accident_labels.json`을 엽니다. 검색(Ctrl+F)으로 `\"reviewed\": false`를 찾으면 아직 검수 안 한 항목을 하나씩 볼 수 있습니다.",
        "2. 항목은 `\"원래 이름\": { \"easy\": \"쉬운 말\", \"reviewed\": false }` 모양입니다. `easy`의 문장을 고치고, 확인이 끝나면 `reviewed`를 `true`로 바꿉니다. **원래 이름(왼쪽 키)은 바꾸면 안 됩니다.**",
        "3. `note`가 붙은 항목은 원래 도표의 뜻이 분명하지 않아 원본 도표(손해보험협회 과실비율 인정기준)로 먼저 확인해야 합니다. 확인한 뒤 `note` 줄은 지워도 됩니다.",
        "4. 고친 뒤 이 표를 새로 만들려면 프로젝트 폴더에서 `docker compose exec -T backend python -m app.label_review > docs/review/accident-labels-review.md`를 실행합니다. (표는 읽기용이라 안 만들어도 화면에는 JSON이 바로 반영됩니다. 서버를 다시 시작하면 적용됩니다.)",
        "",
        "## 검수 기준",
        "",
        "- 뜻이 바뀌지 않아야 합니다. 신호 색(녹색·황색·적색), 선진입/후진입, 비보호 좌회전, 일시정지 위반, 중앙선 침범 같은 말은 쉽게 풀어도 법적 의미가 같아야 합니다.",
        "- 운전을 막 시작한 사람도 읽고 상황을 떠올릴 수 있어야 합니다. 한자어와 도표 약어(선행/후행, 대로/소로 등)는 풀어 씁니다.",
        "- '내 차'와 '상대 차'는 화면에서 이미 구분해 보여 주므로 이 이름에는 넣지 않습니다. (예: \"뒤따르던 차가 직진\")",
        "- 너무 길지 않게 한 줄로 씁니다.",
        "",
    ]
    total = unchecked = flagged = 0
    for key, title, _ in KINDS:
        lines += [f"## {title}", "", "| 검수 | 원래 이름 (과실표) | 쉬운 말 | 확인할 점 |", "| --- | --- | --- | --- |"]
        for original, entry in data[key].items():
            total += 1
            unchecked += 0 if entry["reviewed"] else 1
            flagged += 1 if entry.get("note") else 0
            note = entry.get("note", "").replace("|", "/")
            lines.append(f"| {'[x]' if entry['reviewed'] else '[ ]'} | {original.replace('|', '/')} | {entry['easy']} | {note} |")
        lines.append("")
    lines.insert(2, f"전체 {total}개 중 검수 전 {unchecked}개, 원본 도표 확인이 필요한 항목 {flagged}개입니다.")
    lines.insert(3, "")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render())
