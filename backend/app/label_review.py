"""검수하기 좋은 표(마크다운)를 만든다.

    python -m app.label_review > docs/review/accident-labels-review.md      # 사고 유형 이름의 쉬운 말 (app/data/accident_labels.json)
    python -m app.label_review pdf > docs/review/pdf-adjustment-review.md   # PDF 에서 합친 가감요소 규칙과 쉬운 말 (model/avly/data)
"""

import json
import sys

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


def render_pdf_adjustments() -> str:
    data_dir = catalog.BASE_DIR / "model" / "avly" / "data"
    load = lambda name: json.loads((data_dir / name).read_text(encoding="utf-8"))
    rules, explanations, labels, blocked = load("adjustment_rules.json"), load("adjustment_explanations.json")["factors"], load("factor_labels.json"), load("pdf_rules_blocked.json")
    pdf_types = {k: t for k, t in rules.items() if any("pdf_source" in r for r in t["rules"])}
    pdf_rules = [(k, r) for k, t in pdf_types.items() for r in t["rules"]]
    pending = {k: t["source_review_pending"] for k, t in rules.items() if t.get("source_review_pending")}
    usage = {}
    for k, r in pdf_rules:
        u = usage.setdefault(r["factor"], {"types": set(), "deltas": set(), "actors": set()})
        u["types"].add(k)
        u["deltas"].add(r["delta_pp"])
        u["actors"].add(r["actor"])
    new_factors = sorted((f for f in explanations if f.startswith("pdf_")), key=lambda f: -len(usage.get(f, {"types": ()})["types"]))
    out_of_range = []
    for k, r in pdf_rules:
        base_a = rules[k]["expected_base"][0]
        if not 0 <= (base_a + r["delta_pp"] if r["actor"] == "A" else base_a - r["delta_pp"]) <= 100:
            out_of_range.append(k)
    unreviewed_rules = sum(1 for _, r in pdf_rules if not r.get("reviewed"))
    unreviewed_text = sum(1 for f in new_factors if not explanations[f]["reviewed"])

    L = ["# PDF 가감요소 규칙 검수", "",
         f"손해보험협회 과실비율 인정기준(2023.06) PDF에서 팀원이 뽑은 가감요소를 기존 `adjustment_rules.json`에 합쳤습니다. "
         f"가감요소가 등록된 유형은 **7개에서 {len(rules)}개**(133개 중)가 되었고, 새로 들어온 규칙은 **{len(pdf_rules)}개**(유형 {len(pdf_types)}개), 쉬운 말은 **{len(new_factors)}개**입니다.",
         f"검수 전 규칙 {unreviewed_rules}개, 검수 전 쉬운 말 {unreviewed_text}개입니다. 숫자가 틀리면 과실비율이 틀리므로 서비스에 쓰기 전에 사람이 확인해야 합니다.", "",
         "## 검수 방법", "",
         "### 가장 쉬운 방법: 검수 페이지 (JSON을 열지 않아도 됩니다)",
         "1. **프로젝트를 실행한 상태(`docker compose up`)에서 브라우저로 http://localhost:5173/review.html 을 엽니다**(가장 확실합니다). 파일 [review.html](review.html)을 직접 열 때는 Chrome이나 Edge 창에 파일을 끌어다 놓으세요. 더블클릭은 이 PC의 .html 기본 프로그램이 브라우저가 아니면 열리지 않습니다. 위쪽에 이름을 적습니다.",
         "2. 카드를 열어 적힌 내용이 PDF 원문과 맞는지 보고 **맞아요 / 틀려요 / 모르겠어요**를 누릅니다. 쉬운 문장 탭에서는 문장을 바로 고칠 수도 있습니다. 중간에 닫아도 자동 저장됩니다.",
         "3. 다 하면 **내보내기**를 눌러 받은 파일(`검수결과_이름_날짜.json`)을 담당자에게 보냅니다.",
         "4. 담당자는 받은 파일을 한 폴더에 모아 `docker compose exec backend python tools/apply_review.py 파일1.json 파일2.json`을 실행합니다. 모두 맞다고 확인한 유형만 켜지고, 틀린 곳은 [review-issues.md](review-issues.md)에 모입니다. 두 사람의 결정이 다르면 반영하지 않고 이슈로 남깁니다.",
         "5. 얼마나 됐는지는 `docker compose exec backend python -m app.review_status`로 봅니다.",
         "6. 규칙이나 문장이 바뀌면 `docker compose exec -T backend python tools/make_review_page.py > docs/review/review.html`로 페이지를 다시 만듭니다.", "",
         "아래 \"JSON을 직접 고치는 방법\"은 위 방법을 쓰지 않을 때만 필요합니다.", "",
         "### 1. 규칙(숫자) 검수 — `backend/model/avly/data/adjustment_rules.json` (JSON을 직접 고치는 방법)",
         "**검수하는 단위는 규칙 하나하나가 아니라 유형 하나입니다.** 유형 하나의 규칙을 다 확인했으면 그 유형에 한 번만 표시하면 됩니다.",
         "1. VS Code에서 파일을 열고 확인할 유형 번호(예: `\"60\": {`)로 갑니다. 규칙마다 `pdf_source`가 있습니다. `chart`는 PDF 도표 번호, `raw_text`는 원문에서 뽑은 항목(예: `B 좌회전 금지 위반 +20`), `pdf_pages`는 PDF 쪽수입니다.",
         "2. 원문 PDF의 해당 도표와 맞는지 봅니다: **누구에게(`actor` A/B), 얼마(`delta_pp`), 어떤 항목**인지. 컴퓨터가 이미 규칙 838개의 원문 행·수치·A/B 대응이 추출본과 일치하는 것을 확인했으므로, 추출본 자체가 PDF와 맞는지만 보면 됩니다.",
         "3. 다 맞으면 유형 위쪽의 세 줄을 이렇게 바꿉니다. **이렇게 확인한 유형만 서비스에 켜집니다.** `\"reviewed\": true,` `\"reviewed_by\": \"이름\",` `\"reviewed_at\": \"2026-10-21\",`",
         "4. 틀린 규칙은 `delta_pp`, `actor`를 고치거나 규칙을 지웁니다. (`id`, `factor` 이름은 바꾸지 않습니다.)",
         "5. 누가 어디까지 했는지, 표시가 빠졌거나 어긋난 곳이 있는지는 `docker compose exec backend python -m app.review_status` 한 번으로 볼 수 있습니다. 개발 중에 검수 전 유형도 전부 켜서 보려면 `.env`에 `AVLY_REQUIRE_RULE_REVIEW=0`을 적습니다.", "",
         "### 2. 쉬운 말 검수 — `backend/model/avly/data/adjustment_explanations.json`",
         "아래 표의 문장은 PDF 원문 해설을 읽고 쓴 초안입니다. 고칠 때는 JSON의 `title`, `easy`, `question`을 고치고 확인이 끝나면 `reviewed`를 `true`로 바꿉니다. 질문은 \"예\"라고 답하면 그 요소가 적용되도록, `{who}`(내 차/상대 차) 뒤에 `가`나 `는`이 자연스럽게 붙도록 씁니다. 설명에는 과실이 늘고 주는 방향을 쓰지 않습니다(방향은 +n%p/-n%p로 따로 붙습니다).", "",
         "### 3. 다시 합치기",
         "팀원이 규칙 파일을 고쳐서 다시 주면 `python tools/merge_pdf_rules.py <규칙 파일>`로 새 유형만 합칩니다. 합치기 전에 과실표(CSV)와 기본 비율·진행 이름을 대조하고 하나라도 다르면 멈춥니다.", "",
         f"## 규칙을 넣지 않은 유형 ({len(blocked['blocked_types'])}개)", "",
         "PDF와 과실표(CSV)의 기본 비율이나 조건이 달라 **일부러 뺀 유형**입니다. 이 유형은 기본 비율만 안내합니다. 협회 문서를 보고 어느 쪽이 맞는지, 규칙을 넣을지 결정해 주세요.", "",
         "| 유형 번호 | 이유 |", "| --- | --- |"]
    for k, reasons in blocked["blocked_types"].items():
        L.append(f"| {k} | {' / '.join(reasons).replace('|', '/')} |")
    L += ["", f"## 원문 확인이 남은 유형 ({len(pending)}개)", "",
          "원문에서 역할이나 수치가 불분명한 항목이 있어 **계산에서 뺀** 유형입니다. 사용자가 모든 질문에 답해도 최종 비율을 확정하지 않고 \"확인된 요소만 반영\"으로 안내합니다.", "",
          "| 유형 번호 | 계산에서 뺀 원문 항목 |", "| --- | --- |"]
    for k, items in pending.items():
        L.append(f"| {k} | {' / '.join(items)} |")
    L += ["", "## 값이 특이해서 먼저 볼 것", "",
          f"- **기본 비율에 더하거나 빼면 0~100을 벗어나는 규칙 {len(out_of_range)}개**: 계산 결과는 0~100으로 잘립니다. 이미 100:0인 유형에 가산 항목이 있는 경우 등이며, 원문 표에 실제로 있는 항목인지만 확인하면 됩니다.",
          "- **`신호위반` +20과 +80**: +80은 신호를 어긴 쪽을 일방과실로 보는 도표(33-1 등)의 값입니다. 어느 유형에 적용되는 값인지 확인해 주세요.",
          "- **`좌회전 완료 직후` -30과 -10**: 같은 요소에 두 가지 값이 있습니다. 도표마다 다른 값이 맞는지 확인해 주세요.",
          "- **기존 7개 유형은 기존 규칙을 그대로 뒀습니다.** PDF 규칙과 다른 점: 27번에서 `t_intersection_turn`(+10)이 PDF 쪽에는 없고, PDF는 기존에 영상 관찰로 자동 적용되던 항목(11번 4개, 1번 1개, 126번 2개)을 모두 \"사용자 직접 확인\"으로 표시했습니다. 어느 쪽을 따를지 정해 주세요.",
          "- 새 규칙은 **전부 사용자가 직접 확인**합니다(`manual_only`). 영상 AI가 관찰한 값은 질문 옆에 \"AI 제안\"으로만 보이고 계산에 자동 반영되지 않습니다.", "",
          f"## 새 가감요소 쉬운 말 ({len(new_factors)}개)", "",
          "| 검수 | PDF 원문 이름 | 쉬운 제목 | 쉬운 설명 | 질문 | 가감(%p) | 쓰이는 유형 | 확인할 점 |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    esc = lambda t: (t or "").replace("|", "/").replace("\n", " ")
    for f in new_factors:
        e, u = explanations[f], usage.get(f, {"types": set(), "deltas": set(), "actors": set()})
        deltas = " / ".join(f"{d:+d}" for d in sorted(u["deltas"]))
        L.append(f"| {'[x]' if e['reviewed'] else '[ ]'} | {esc(labels[f])} | {esc(e['title'])} | {esc(e['easy'])} | {esc(e['question'])} | {deltas} | {len(u['types'])}개 유형 | {esc(e.get('note'))} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(render_pdf_adjustments() if sys.argv[1:] == ["pdf"] else render())
