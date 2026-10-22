"""검수 결과 파일들을 한 장의 웹 페이지(docs/review/review-results.html)로 풀어서 보여 준다.

    python tools/make_review_results_page.py 파일1.json 파일2.json ... [-o 출력.html] [--follow 이름]

- 검수 페이지에서 내보낸 `검수결과_이름_날짜.json`, `쉬운말 검수결과_이름_날짜.json` 을 모두 넣으면 된다. 같은 사람이 여러 번 냈으면 가장 늦은 날짜가 '현재 의견'이다.
- `--follow 이름`: 그 사람의 가장 늦은 제출을 기준으로 정한 항목(그 사람이 모든 규칙을 '맞아요'로 낸 유형)은 '결정이 끝난 것'으로 따로 보여 준다.
- 이 도구는 데이터를 바꾸지 않는다. 만들어진 HTML 은 브라우저로 열어서 읽기만 하면 된다 (파일 하나, 인터넷 필요 없음).
- 무엇을 보여 주나: ① 지금 정해야 할 것(쉬운 말로) ② 규칙(숫자)에 문제가 있는 유형: PDF 원문과 우리 데이터를 나란히
  ③ 쉬운 문장: 사용자에게 실제로 보이는 모습과 검수자 의견 ④ 이미 서비스에 반영된 것
"""
import argparse
import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "model"))

from avly.tables import ALL_ADJUSTMENT_RULES, REVIEWED_FACTOR_WORDING, active_rules, type_is_reviewed, wording_gate   # noqa: E402

DATA = BACKEND / "model" / "avly" / "data"
OUT = BACKEND.parent / "docs" / "review" / "review-results.html"
UNIFY = "의진님이 수정하신 내용으로 통일"
e = lambda x: html.escape(str(x if x is not None else ""))
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 검수 파일 읽기
def read_exports(paths):
    """사람별 제출 목록 {이름: [제출(날짜순)]}. 제출 = {'date','types','wording','file'}"""
    by_person = defaultdict(list)
    for p in paths:
        d = load(p)
        by_person[d.get("reviewer") or "(이름 없음)"].append({"date": d.get("date", ""), "types": d.get("types") or {}, "wording": d.get("wording") or {}, "file": Path(p).name})
    for subs in by_person.values():
        subs.sort(key=lambda s: s["date"])
    return by_person


def short_date(d):
    return d[5:] if len(d) == 10 else d


def verdict_label(ok):
    return "맞아요" if ok else "틀려요"


class Ctx:
    def __init__(self, by_person, delete_request, also_check, follow=""):
        self.follow = follow
        self.by_person = by_person
        self.delete_request, self.also_check = set(delete_request), set(also_check)
        self.rules = ALL_ADJUSTMENT_RULES
        self.factors = load(DATA / "adjustment_explanations.json")["factors"]
        self.labels = load(BACKEND / "app" / "data" / "accident_labels.json")
        self.rows = {r["accident_type"]: r for r in csv.DictReader((DATA / "fault_table_car_to_car.csv").open(encoding="utf-8-sig", newline=""))}
        self.reviewed_types = active_rules(self.rules, True)
        self.asked, self.held = wording_gate(self.reviewed_types, REVIEWED_FACTOR_WORDING)
        self.use = defaultdict(set)
        for t, c in self.rules.items():
            for r in c["rules"]:
                self.use[r["factor"]].add(t)

    def easy(self, kind, name):
        name = name.replace("출자", "출차") if "주차구역" in name else name
        return (self.labels.get(kind, {}).get(name) or {}).get("easy") or name

    def situation(self, t):
        r = self.rows[t]
        return {"place": self.easy("places", r["accident_place_name"]), "feature": self.easy("features", r["accident_place_feature_name"]),
                "a": self.easy("progress", r["vehicle_a_progress_info_name"]), "b": self.easy("progress", r["vehicle_b_progress_info_name"]),
                "ratio": f"{r['negligence_a']}:{r['negligence_b']}", "a_raw": r["vehicle_a_progress_info_name"], "b_raw": r["vehicle_b_progress_info_name"]}

    def title(self, factor):
        return (self.factors.get(factor) or {}).get("title") or factor

    def preview(self, factor, who="내 차"):
        f = self.factors.get(factor)
        if not f:
            return None
        return {"title": f["title"], "easy": f["easy"], "question": f["question"].format(who=who), "reviewed": f.get("reviewed", False)}


# ------------------------------------------------------------------ 규칙(숫자) 확인이 필요한 유형 찾기
def is_wording_note(note):
    return "문장" in note or "문구" in note or UNIFY in note


def find_attention(ctx):
    """유형별로 '숫자(규칙)'에 대해 사람이 확인해야 할 이유를 모은다. {유형: [이유...]}"""
    why = defaultdict(list)
    latest = {}   # (이름, 유형) -> 가장 늦은 제출의 결정
    for person, subs in ctx.by_person.items():
        for s in subs:
            for t, v in s["types"].items():
                for rid, r in (v.get("rules") or {}).items():
                    if not r.get("ok") and not is_wording_note(r.get("note") or ""):
                        why[t].append(f"{person}({short_date(s['date'])})이 규칙 `{rid}`를 '틀려요'로 표시했습니다" + (f": {r['note']}" if r.get("note") else ""))
                latest[(person, t)] = (s, v)
    for t in {t for _, t in latest}:
        decisions = {p: v["decision"] for (p, tt), (s, v) in latest.items() if tt == t}
        if len(set(decisions.values())) > 1:
            why[t].append("검수자 의견이 다릅니다: " + ", ".join(f"{p} {'맞아요' if d == 'ok' else '문제 있음'}" for p, d in sorted(decisions.items())))
        for (p, tt), (s, v) in latest.items():
            if tt == t and t in ctx.rules:
                missing = {r["id"] for r in ctx.rules[t]["rules"]} - set(v.get("rules") or {})
                if missing:
                    why[t].append(f"{p}({short_date(s['date'])})이 규칙 {len(missing)}개({', '.join(sorted(missing))})에 대한 결정을 빠뜨렸습니다")
    resolved = {}
    if ctx.follow:   # 기준으로 삼은 사람이 모든 규칙을 '맞아요'로 낸 유형은 결정이 끝난 것으로 본다
        for (p, t), (s, v) in latest.items():
            if p == ctx.follow and t in why and v["decision"] == "ok" and all(r.get("ok") for r in (v.get("rules") or {}).values()) \
                    and t in ctx.rules and set(v.get("rules") or {}) == {r["id"] for r in ctx.rules[t]["rules"]}:
                resolved[t] = (f"{p} {short_date(s['date'])} 제출 기준으로 맞다고 결정", why.pop(t))
    for t in [t for t in why if t not in ctx.rules and t in ctx.rows]:   # 검수 결정으로 규칙을 지운 유형
        resolved[t] = ("검수 결정으로 가감요소 규칙을 삭제함 (기본 비율만 안내)", why.pop(t))
    reviewed_somewhere = {t for subs in ctx.by_person.values() for sub in subs for t in sub["types"]}
    for t in reviewed_somewhere - set(ctx.rules):   # 검수 파일에는 있지만 규칙에서 삭제된 유형(지적이 없었어도 보여 준다)
        if t in ctx.rows and t not in resolved:
            resolved[t] = ("검수 결정으로 가감요소 규칙을 삭제함 (기본 비율만 안내)", [])
    for t in ctx.delete_request:
        why[t].append("삭제 요청이 있습니다 (삭제하기 전에 한 번 더 확인하기로 함)")
    for t in ctx.also_check:
        why[t].append("삭제 요청 대상 유형과 같은 모양이라 같이 확인이 필요합니다 (검수자는 맞다고 했음)")
    return why, resolved


# ------------------------------------------------------------------ HTML 조각
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1f2933;--muted:#667085;--line:#dfe3e8;--ok:#12805c;--okbg:#e5f6ef;--bad:#c2371f;--badbg:#fdeeea;--warn:#8a5a00;--warnbg:#fff6df;--accent:#2f5bea;--accentbg:#eaf0ff}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--text:#e8ebf0;--muted:#9aa3b2;--line:#2e3540;--ok:#5fd3a4;--okbg:#17332a;--bad:#ff8a73;--badbg:#3a1f1a;--warn:#f0c36a;--warnbg:#38301a;--accent:#8aa8ff;--accentbg:#1e2a4a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.65 system-ui,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0}header nav{display:flex;gap:6px;flex-wrap:wrap}header nav a{padding:4px 10px;border:1px solid var(--line);border-radius:14px;color:var(--text);text-decoration:none;font-size:13px}
header input{margin-left:auto;padding:7px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text);min-width:220px;font:inherit}
main{max-width:1120px;margin:0 auto;padding:20px}h2{font-size:20px;margin:34px 0 6px}h3{font-size:16px;margin:0}p{margin:6px 0}
.lead{color:var(--muted)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}.stat b{display:block;font-size:26px}
.badge{display:inline-block;padding:1px 9px;border-radius:11px;font-size:12px;font-weight:700;border:1px solid var(--line);margin-right:4px}
.b-ok{background:var(--okbg);color:var(--ok)}.b-bad{background:var(--badbg);color:var(--bad)}.b-warn{background:var(--warnbg);color:var(--warn)}.b-info{background:var(--accentbg);color:var(--accent)}
.problem{border-left:4px solid var(--warn)}.problem h3{margin-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}th{background:var(--bg);font-weight:700}
details{margin:10px 0}summary{cursor:pointer;font-weight:700}
.type{border-left:4px solid var(--line)}.type.attn{border-left-color:var(--bad)}.type header{all:unset}
.vehicles{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 0}.veh{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px}.veh b{display:block;font-size:12px;color:var(--muted)}
.reason{background:var(--warnbg);color:var(--text);border-radius:8px;padding:8px 12px;margin:8px 0}.reason li{margin:2px 0}
.note{background:var(--badbg);border-radius:6px;padding:4px 8px;display:inline-block}.sug{background:var(--okbg);border-radius:6px;padding:4px 8px;display:inline-block}
.preview{background:var(--accentbg);border-radius:8px;padding:8px 12px}.preview q{quotes:none;font-weight:700}
.muted{color:var(--muted);font-size:13px}.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.hide{display:none}@media(max-width:700px){.vehicles{grid-template-columns:1fr}header input{margin-left:0;width:100%}}
@media print{header{position:static}}
"""

JS = """
const q=document.getElementById('q');
q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();document.querySelectorAll('.item').forEach(el=>{el.classList.toggle('hide',v&&!el.textContent.toLowerCase().includes(v));if(v&&!el.classList.contains('hide')&&el.tagName==='DETAILS')el.open=true;});});
"""


def badge(text, kind):
    return f'<span class="badge b-{kind}">{e(text)}</span>'


def person_marks(ctx, t, rid):
    """규칙 하나에 대한 검수자별 의견(제출 순서대로)."""
    out = []
    for person, subs in sorted(ctx.by_person.items()):
        for s in subs:
            r = ((s["types"].get(t) or {}).get("rules") or {}).get(rid)
            if r is None:
                continue
            note = (r.get("note") or "").strip()
            if r.get("ok") and not note:
                out.append(f'<div class="muted">{e(person)} ({short_date(s["date"])}): 맞아요</div>')
            else:
                kind = "bad" if not r.get("ok") else "warn"
                out.append(f'<div>{badge(person + " " + short_date(s["date"]) + " · " + (verdict_label(r.get("ok")) if not r.get("ok") else "맞아요(메모)"), kind)}'
                           + (f'<span class="note">{e(note)}</span>' if note else "") + "</div>")
    return "".join(out) or '<span class="muted">의견 없음</span>'


def type_card(ctx, t, reasons):
    s = ctx.situation(t)
    conf = ctx.rules.get(t)
    status = []
    if t in ctx.delete_request:
        status.append(badge("삭제 요청", "bad"))
    if conf is None:
        status.append(badge("규칙 없음", "warn"))
    elif t in ctx.asked:
        status.append(badge("서비스에서 가감요소를 묻는 중", "ok"))
    elif type_is_reviewed(conf):
        status.append(badge("규칙은 검수 완료 · 쉬운 말 검수 전이라 묻지 않음", "info"))
    else:
        status.append(badge("꺼져 있음(검수 전)", "warn"))
    rows = []
    gs = []
    for r in conf["rules"] if conf else []:
        if r["factor"] in ("gross_negligence", "serious_negligence"):
            gs.append(f"{r['actor']} {r['delta_pp']:+d}")
            continue
        src = r.get("pdf_source") or {}
        raw = src.get("raw_text") or "(원문 정보 없음)"
        pages = ", ".join(str(p) for p in (src.get("pdf_pages") or []))
        rows.append(f"<tr><td>{e(ctx.title(r['factor']))}<div class='muted mono'>{e(r['id'])}</div></td>"
                    f"<td>{e(raw)}<div class='muted'>{e(src.get('chart') or '')}{' · PDF ' + e(pages) + '쪽' if pages else ''}</div></td>"
                    f"<td><b>{e(r['actor'])} 차량</b> {r['delta_pp']:+d}%p</td><td>{person_marks(ctx, t, r['id'])}</td></tr>")
    gs_note = f"<p class='muted'>현저한/중대한 과실({', '.join(gs)})은 모든 유형에 공통이라 표에서 뺐습니다.</p>" if gs else ""
    reason_html = "".join(f"<li>{e(x)}</li>" for x in reasons)
    pages_all = sorted({p for r in (conf["rules"] if conf else []) for p in ((r.get("pdf_source") or {}).get("pdf_pages") or [])})
    return (f'<details class="card type item attn" id="t{t}" open><summary>유형 {t} · {e(s["place"])} · {e(s["feature"])} {"".join(status)}</summary>'
            f'<div class="vehicles"><div class="veh"><b>표의 A 차량 (원문 그대로: {e(s["a_raw"])})</b>{e(s["a"])}</div>'
            f'<div class="veh"><b>표의 B 차량 (원문 그대로: {e(s["b_raw"])})</b>{e(s["b"])}</div></div>'
            f'<p>기본 과실비율 A:B = <b>{e(s["ratio"])}</b></p>'
            f'<div class="reason"><b>왜 확인이 필요한가</b><ul>{reason_html}</ul></div>'
            + (f'<table><tr><th>가감요소</th><th>PDF 원문 (추출한 글)</th><th>우리 데이터에서 붙은 차량·값</th><th>검수자 의견</th></tr>{"".join(rows)}</table>' if rows else "<p class='muted'>가감요소 규칙이 없습니다.</p>")
            + gs_note + (f'<p class="muted">직접 확인하려면 인정기준 PDF의 {e(", ".join(str(p) for p in pages_all[:6]))}쪽 부근을 보세요.</p>' if pages_all else "") + "</details>")


# ------------------------------------------------------------------ 쉬운 문장
def wording_rows(ctx):
    """요소별로 현재 문장, 검수자 의견, 제안 문장을 모은다."""
    items = defaultdict(lambda: {"kim": None, "notes": [], "sugg": []})
    for person, subs in ctx.by_person.items():
        for s in subs:
            for f, d in s["wording"].items():
                items[f]["kim"] = (person, s["date"], d) if (items[f]["kim"] is None or items[f]["kim"][1] <= s["date"]) else items[f]["kim"]
            for t, v in s["types"].items():
                for rid, r in (v.get("rules") or {}).items():
                    n = (r.get("note") or "").strip()
                    if n and is_wording_note(n) and UNIFY not in n:
                        f = rid.split("_", 2)[2]
                        pair = (person, short_date(s["date"]), n)
                        if pair not in items[f]["sugg"]:
                            items[f]["sugg"].append(pair)
    return items


def wording_section(ctx):
    items = wording_rows(ctx)
    status_of = lambda f: "쓰는 중" if ctx.factors.get(f, {}).get("reviewed") else "보류"
    rows = []
    for f in sorted(items, key=lambda k: (-len(ctx.use[k]), k)):
        info, entry = items[f], ctx.factors.get(f)
        if entry is None:
            continue
        kim = info["kim"]
        decision = kim[2]["decision"] if kim else None
        opinion = []
        if kim:
            label = {"ok": ("괜찮아요", "ok"), "issue": ("문제 있음", "bad"), "edit": ("직접 고침", "info")}.get(decision, (decision, "warn"))
            opinion.append(badge(f"{kim[0]} · {label[0]}", label[1]))
            if kim[2].get("note"):
                opinion.append(f'<span class="note">{e(kim[2]["note"])}</span>')
            if decision == "edit":
                opinion.append(f'<div class="sug">고친 문장: {e(kim[2].get("title"))} / {e(kim[2].get("easy"))} / {e(kim[2].get("question"))}</div>')
        for person, d, n in info["sugg"]:
            opinion.append(f'<div>{badge(person + " " + d + " · 제안", "warn")}<span class="sug">{e(n)}</span></div>')
        pv = ctx.preview(f)
        preview = (f'<div class="preview"><q>{e(pv["question"])}</q><div class="muted">{e(pv["easy"])}</div></div>' if pv else "")
        st = status_of(f)
        rows.append(f'<tr class="item"><td><b>{e(entry["title"])}</b><div class="muted mono">{e(f)}</div>{badge(st, "ok" if st == "쓰는 중" else "warn")}</td>'
                    f'<td>{preview}</td><td>{"".join(opinion) or "<span class=muted>의견 없음</span>"}</td><td>{len(ctx.use[f])}개 유형</td></tr>')
    return rows


# ------------------------------------------------------------------ 전체 페이지
def build(ctx):
    why, resolved = find_attention(ctx)
    total_types = len(ctx.rows)
    n_ok_words = len(REVIEWED_FACTOR_WORDING)
    people = sorted(ctx.by_person)
    reviewer_rows = []
    for p in people:
        for s in ctx.by_person[p]:
            kinds = []
            if s["types"]:
                dec = defaultdict(int)
                for v in s["types"].values():
                    dec[v["decision"]] += 1
                kinds.append(f"규칙(숫자) 검수 {len(s['types'])}개 유형 (맞아요 {dec['ok']}, 문제 {dec['issue']})")
            if s["wording"]:
                dec = defaultdict(int)
                for v in s["wording"].values():
                    dec[v["decision"]] += 1
                kinds.append(f"쉬운 문장 {len(s['wording'])}개 (괜찮아요 {dec['ok']}, 문제 {dec['issue']}, 직접 고침 {dec['edit']})")
            reviewer_rows.append(f"<tr><td>{e(p)}</td><td>{e(s['date'])}</td><td>{'<br>'.join(kinds)}</td><td class='muted'>{e(s['file'])}</td></tr>")

    resolved_rows = "".join(
        f"<tr class='item'><td><b>유형 {t}</b><div class='muted'>{e(ctx.situation(t)['place'])} · {e(ctx.situation(t)['feature'])}</div></td><td>{e(note)}</td><td><ul>{''.join('<li>' + e(x) + '</li>' for x in reasons)}</ul></td></tr>"
        for t, (note, reasons) in sorted(resolved.items(), key=lambda kv: int(kv[0])) if t in ctx.rows)
    attn_cards = [type_card(ctx, t, why[t]) for t in sorted(why, key=int) if t in ctx.rows]
    word_rows = wording_section(ctx)
    n_supported = len(ctx.asked)

    left = sorted(why, key=int)
    left_items = "".join(f"<li><a href='#t{t}'>유형 {t}</a> — {e(why[t][0])}</li>" for t in left if t in ctx.rows)
    gross_unreviewed = not ctx.factors.get("gross_negligence", {}).get("reviewed")
    problems = (
        (f"<div class='card problem'><h3>① 규칙(숫자)에서 아직 확인이 필요한 유형: {len(left)}개</h3><ul>{left_items}</ul>"
         "<p class='muted'>아래 '규칙(숫자) 확인이 필요한 유형'에서 PDF 원문과 우리 데이터를 나란히 볼 수 있습니다.</p></div>") if left else
        "<div class='card'><h3>① 규칙(숫자)에서 아직 확인이 필요한 유형은 없습니다</h3></div>"
    ) + (
        (f"<div class='card'><h3>② 결정이 끝난 유형: {len(resolved)}개</h3><p>의견이 엇갈렸거나 지적이 있었지만 {e(ctx.follow)}님의 최신 제출 기준으로 맞다고 정해 서비스에 반영했습니다. 목록은 아래 '결정이 끝난 것'에 있습니다.</p></div>") if resolved else ""
    ) + (
        f"<div class='card problem'><h3>③ 사용자에게 보이는 쉬운 문장: 검수 완료 {n_ok_words}개 / 전체 {len(ctx.factors)}개</h3>"
        "<p>검수 완료된 문장만 서비스에서 묻고 계산합니다. 나머지 문장은 아래 '쉬운 문장' 표에서 <b>보류</b>로 표시됩니다. 표에서 사용자에게 실제로 어떻게 보이는지와 검수자 의견·제안을 볼 수 있습니다."
        + (" 특히 <b>'현저한 과실'은 새 문장이 아직 없습니다.</b>" if gross_unreviewed else "")
        + "</p></div>"
    )

    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>검수 결과 한눈에 보기</title><style>{CSS}</style></head><body>
<header><h1>검수 결과 한눈에 보기</h1><nav><a href="#now">지금 정할 것</a><a href="#rules">규칙(숫자) 확인 유형</a><a href="#decided">결정이 끝난 것</a><a href="#words">쉬운 문장</a><a href="#done">이미 반영된 것</a><a href="#who">검수자별</a></nav><input id="q" type="search" placeholder="검색 (유형 번호, 문장, 검수자…)"></header>
<main>
<p class="lead">검수 파일 {sum(len(v) for v in ctx.by_person.values())}개를 풀어서 보여 줍니다. 이 페이지는 읽기 전용이고 데이터를 바꾸지 않습니다.</p>
<div class="card"><b>용어</b><ul><li><b>표의 A·B 차량</b>: 과실표의 차량 구분입니다. 화면에서는 "내 차/상대 차"로 보여 줍니다.</li><li><b>가감요소</b>: 기본 과실비율에서 +n%p, −n%p로 조정되는 사정입니다. (예: 서행하지 않았다 +10)</li><li><b>규칙(숫자) 검수</b>: 유형별로 가감요소가 맞는 차량에 맞는 값으로 붙어 있는지 PDF와 대조하는 것. <b>쉬운 문장 검수</b>: 사용자에게 보이는 제목·설명·질문이 이해되고 오해가 없는지 보는 것.</li></ul></div>

<h2 id="now">지금 상태와 남은 것</h2>
<div class="grid"><div class="card stat"><b>{n_supported}개</b>가감산까지 지원하는 유형 (전체 {total_types}개)</div>
<div class="card stat"><b>{len(attn_cards)}개</b>규칙(숫자) 확인이 필요한 유형</div>
<div class="card stat"><b>{len(ctx.factors) - n_ok_words}개</b>검수 전 쉬운 문장 (검수 완료 {n_ok_words}개)</div></div>
{problems}

<h2 id="rules">규칙(숫자) 확인이 필요한 유형 ({len(attn_cards)}개)</h2>
<p class="lead">각 유형을 열면 <b>PDF 원문에서 추출한 글</b>과 <b>우리 데이터에서 붙은 차량·값</b>을 나란히 볼 수 있습니다. 원문의 A/B가 어느 차량인지는 PDF에서 직접 확인해야 합니다.</p>
{"".join(attn_cards)}

{('<h2 id="decided">결정이 끝난 것 (' + str(len(resolved)) + '개 유형)</h2><p class="lead">검수 과정에서 의견이 엇갈리거나 지적이 있었지만, 기준으로 삼은 제출(' + e(ctx.follow) + ' 최신 제출)에 따라 맞다고 정해서 서비스에 반영한 유형입니다. 데이터는 바뀌지 않았습니다.</p><table><tr><th style="width:18%">유형</th><th style="width:25%">결정</th><th>있었던 의견</th></tr>' + resolved_rows + '</table>') if resolved else ''}

<h2 id="words">쉬운 문장 ({len(word_rows)}개) — 사용자에게 이렇게 보여요</h2>
<p class="lead">파란 상자가 사용자 화면에 나오는 질문과 설명입니다. 많은 유형에 쓰이는 문장부터 정렬했습니다. <b>보류</b>는 검수가 끝나지 않아 지금 서비스에서 쓰지 않는 문장입니다.</p>
<table><tr><th style="width:20%">가감요소</th><th style="width:30%">사용자에게 보이는 모습 (내 차 기준)</th><th>검수자 의견·제안</th><th style="width:9%">쓰이는 곳</th></tr>{"".join(word_rows)}</table>

<h2 id="done">이미 서비스에 반영된 것</h2>
<div class="card"><p>규칙(숫자) 검수 완료 유형 {len(ctx.reviewed_types)}개 중 쉬운 문장까지 확인된 가감요소가 있어서 <b>실제로 가감요소를 묻는 유형은 {n_supported}개</b>입니다. 자세한 목록은 <span class="mono">docs/review/supported-types.md</span>에 있습니다.</p>
<p class="muted">나머지 유형은 기본 과실비율만 안내하거나, 쉬운 문장이 검수된 가감요소만 반영해서 "확인한 요소만 반영한 비율"로 안내합니다.</p></div>

<h2 id="who">검수자별 제출 현황</h2>
<table><tr><th>검수자</th><th>날짜</th><th>내용</th><th>파일</th></tr>{"".join(reviewer_rows)}</table>
</main><script>{JS}</script></body></html>"""
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exports", nargs="+", type=Path, help="검수 페이지에서 내보낸 결과 파일")
    parser.add_argument("-o", "--output", type=Path, default=OUT)
    parser.add_argument("--delete-request", default="", help="삭제 요청이 있는 유형 번호(쉼표로 구분)")
    parser.add_argument("--also-check", default="", help="같은 모양이라 같이 확인하려는 유형 번호")
    parser.add_argument("--follow", default="", help="이 사람의 가장 늦은 제출을 기준으로 정한 항목은 '결정이 끝난 것'으로 보여 준다")
    args = parser.parse_args(argv)
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    ctx = Ctx(read_exports(args.exports), split(args.delete_request), split(args.also_check), args.follow)
    args.output.write_text(build(ctx), encoding="utf-8")
    print("저장했습니다:", args.output)


if __name__ == "__main__":
    main()
