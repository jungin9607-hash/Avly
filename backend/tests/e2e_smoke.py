"""실행 중인 서버(api + worker + DB)를 실제 HTTP 로 끝까지 써 보는 확인 스크립트. 표준 라이브러리만 쓴다.

  python tests/e2e_smoke.py                       # 기본 주소 http://localhost:8000
  API_BASE=http://api:8000 python tests/e2e_smoke.py

worker 가 ENGINE=fake (또는 replay) 일 때 동작한다. 영상 첫 줄의 'FAKE ...' 지시로 지원하지 않는 사고 같은 경우를 만든다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")
CONSENT = {"version": "e2e", "analysis": True, "retention": False}
failures = []


def call(method, path, body=None, headers=None, raw=False):
    data = None
    headers = dict(headers or {})
    if body is not None and not isinstance(body, bytes):
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif isinstance(body, bytes):
        data = body
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload or b"null"))
    except urllib.error.HTTPError as e:
        payload = e.read()
        return e.code, (payload if raw else json.loads(payload or b"null"))


def multipart(filename, content):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: video/mp4\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def check(name, condition, detail=""):
    print(("  ✓ " if condition else "  ✗ ") + name + ("" if condition else f"  ← {detail}"))
    if not condition:
        failures.append(name)


def wait(analysis_id, headers, until, timeout=60):
    seen = []
    end = time.time() + timeout
    while time.time() < end:
        _, view = call("GET", f"/api/v1/analyses/{analysis_id}", headers=headers)
        label = view["status"] + (f"/{view['stage']['id']}" if view["stage"] else "")
        if not seen or seen[-1] != label:
            seen.append(label)
        if view["status"] in until:
            return view, seen
        time.sleep(0.3)
    raise SystemExit(f"시간 초과: {seen}")


def start(content):
    status, acc = call("POST", "/api/v1/accidents", {"title": "e2e", "consent": CONSENT})
    assert status == 201, acc
    headers = {"X-Session-Id": acc["session_id"]}
    body, h = multipart("black.mp4", content)
    status, _ = call("POST", f"/api/v1/accidents/{acc['id']}/videos", body, {**headers, **h})
    assert status == 201
    status, started = call("POST", f"/api/v1/accidents/{acc['id']}/analyses", headers=headers)
    assert status == 202, started
    return acc["id"], headers, started["analysis_id"]


def main():
    print("1) 상태 확인")
    check("서버 응답", call("GET", "/health")[1] == {"status": "ok"})
    check("DB 연결", call("GET", "/health/db")[1]["status"] == "ok")

    print("2) 전체 흐름: 업로드 → 분석 → 확인 → 가감 질문 → 결과")
    accident_id, headers, analysis_id = start(b"ordinary video bytes")
    view, seen = wait(analysis_id, headers, {"awaiting_confirmation", "failed", "unsupported"})
    print("    상태 변화:", " → ".join(seen))
    check("확인 대기에 도달", view["status"] == "awaiting_confirmation", view)
    situation = view["situation"]
    check("AI 후보가 있음", bool(situation["candidates"]) and situation["default_index"] == 0)
    candidate = situation["candidates"][situation["default_index"]]
    _, q = call("GET", f"/api/v1/analyses/{analysis_id}/adjustment-questions?accident_type_id={candidate['accident_type_id']}&role={candidate['role']}", headers=headers)
    check("가감요소 질문이 쉬운 말로 옴", q["registered"] and all(x["easy"] and x["question"] for x in q["questions"]))
    answers = [{"key": x["key"], "answer": "아니요"} for x in q["questions"]]
    for a in answers:
        if a["key"].endswith("signal_delay"):
            a["answer"] = "예"
    status, _ = call("POST", f"/api/v1/analyses/{analysis_id}/confirm",
                     {"accident_type_id": candidate["accident_type_id"], "role": candidate["role"], "answers": answers}, headers)
    check("확인 접수(202)", status == 202)
    view, seen = wait(analysis_id, headers, {"completed", "failed"})
    check("결과 완료", view["status"] == "completed", view)
    result = view["result"]
    check("최종 비율과 단계", result["state"] == "final" and len(result["steps"]) >= 2, result.get("state"))
    print(f"    기본 {result['fault']['base']} → 최종 {result['fault']['final']}")
    check("타임라인이 있음", bool(result["timeline"]))
    _, video = call("GET", f"/api/v1/accidents/{accident_id}/video-url", headers=headers)
    check("비식별 영상 주소(개발용 복사)", video["available"])
    if video["available"]:
        status, content = call("GET", video["url"], raw=True)
        check("영상 내려받기", status == 200 and content == b"ordinary video bytes")

    print("3) 다른 사람은 볼 수 없음")
    other = {"X-Session-Id": str(uuid.uuid4())}
    check("남의 분석은 404", call("GET", f"/api/v1/analyses/{analysis_id}", headers=other)[0] == 404)
    check("남의 사고는 404", call("GET", f"/api/v1/accidents/{accident_id}", headers=other)[0] == 404)
    check("세션 없으면 401", call("GET", f"/api/v1/analyses/{analysis_id}")[0] == 401)

    print("4) 지원하지 않는 사고")
    _, h2, a2 = start("FAKE unsupported 차대보행자\n".encode())
    view, _ = wait(a2, h2, {"unsupported", "failed", "awaiting_confirmation"})
    check("unsupported 로 끝남", view["status"] == "unsupported" and "차대보행자" in view["unsupported_reason"], view)

    print("5) 너무 긴 영상, 분석 실패")
    _, h3, a3 = start(b"FAKE too_long 55\n")
    view, _ = wait(a3, h3, {"failed", "awaiting_confirmation"})
    check("VIDEO_TOO_LONG", view["status"] == "failed" and view["error"]["code"] == "VIDEO_TOO_LONG", view)
    _, h4, a4 = start(b"FAKE fail\n")
    view, _ = wait(a4, h4, {"failed", "awaiting_confirmation"})
    check("ANALYSIS_FAILED", view["status"] == "failed" and view["error"]["code"] == "ANALYSIS_FAILED", view)

    print("6) 표에 맞는 유형이 없을 때")
    _, h5, a5 = start(b"FAKE fixture parking\n")
    view, _ = wait(a5, h5, {"awaiting_confirmation", "failed"})
    check("후보는 참고용이고 미리 고르지 않음", view["situation"]["default_index"] is None and view["situation"]["candidates"])
    call("POST", f"/api/v1/analyses/{a5}/confirm", {"accident_type_id": None}, h5)
    view, _ = wait(a5, h5, {"completed", "failed"})
    check("확정 불가(unresolved)", view["status"] == "completed" and view["result"]["state"] == "unresolved" and view["result"]["fault"] is None, view)

    print()
    if failures:
        print(f"실패 {len(failures)}건: {failures}")
        sys.exit(1)
    print("모두 통과")


if __name__ == "__main__":
    main()
