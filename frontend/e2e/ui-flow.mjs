// 실제 브라우저(Chromium)로 화면을 끝까지 눌러 보는 확인 스크립트.
// 업로드 → 동의 → 분석 → 사고 상황 확인 → 가감 질문 → 결과 → 타임라인 → 유사 판례, 그리고 지원하지 않는 사고·긴 영상·유형 없음·다른 브라우저까지 본다.
//
// 먼저 서버를 띄운다 (docker compose up -d). worker 가 기본값(ENGINE=fake, REDACTION=dev_copy)이어야 한다.
// 실행: frontend/e2e/README.md 참고. 화면 사진은 SHOTS_DIR 에 저장되니 눈으로도 확인한다.
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.APP_URL ?? "http://localhost:5173";
const SHOTS = process.env.SHOTS_DIR ?? "./shots";
fs.mkdirSync(SHOTS, { recursive: true });
const results = [];
const ok = (name, cond, detail = "") => { results.push([name, !!cond]); console.log((cond ? "  ✓ " : "  ✗ ") + name + (cond ? "" : "  ← " + detail)); };

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "ko-KR" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });
const shot = (name) => page.screenshot({ path: `${SHOTS}/${name}.png` });

async function upload(content, name = "sample.mp4") {
  await page.goto(BASE + "/upload");
  await page.setInputFiles('input[type="file"]', { name, mimeType: "video/mp4", buffer: Buffer.from(content) });
}

console.log("1) 정상 흐름: 업로드 → 동의 → 분석 → 사고 상황 확인 → 가감 질문 → 결과");
await upload("ordinary video bytes");
await page.getByText("블랙박스 영상 수집 동의").waitFor();
const startBtn = page.getByRole("button", { name: /동의하고 영상 분석 시작하기/ });
ok("분석 동의 전에는 시작 버튼이 비활성", await startBtn.isDisabled());
await shot("01-consent");
await page.getByText("영상 분석과 외부 AI 서비스 이용 동의").click();
ok("분석 동의만으로는 시작 버튼이 비활성(당사자 영상 확인 필요)", await startBtn.isDisabled());
await page.getByText("내 차가 사고에 직접 관여한 영상이에요").click();
ok("동의와 당사자 영상 확인을 하면 시작 버튼이 활성", await startBtn.isEnabled());
await startBtn.click();
await page.getByText("AI가 분석한 사고 상황이 맞나요?").waitFor({ timeout: 30000 });
await shot("02-situation");
const selects = page.locator("select.md-select");
ok("네 항목이 AI 후보로 미리 채워짐", (await selects.evaluateAll((els) => els.map((e) => e.value))).every(Boolean), await selects.evaluateAll((els) => els.map((e) => e.value)).then(String));
ok("기본 비율 안내가 보임", await page.getByText(/기본 책임은/).isVisible());
const firstValues = await selects.evaluateAll((els) => els.map((e) => e.value));
console.log("    AI 후보:", firstValues.join(" / "));
// 앞 항목을 바꾸면 뒤 항목이 비워진다
const placeOptions = await selects.nth(0).locator("option").allTextContents();
await selects.nth(0).selectOption({ index: placeOptions.findIndex((t) => t !== firstValues[0] && t !== "선택해 주세요") });
ok("장소를 바꾸면 뒤 항목이 비워지고 다음 버튼이 비활성", (await selects.nth(1).inputValue()) === "" && (await page.getByRole("button", { name: /맞아요, 다음으로/ }).isDisabled()));
await selects.nth(0).selectOption(firstValues[0]);
await selects.nth(1).selectOption(firstValues[1]);
await selects.nth(2).selectOption(firstValues[2]);
await selects.nth(3).selectOption(firstValues[3]);
await page.getByRole("button", { name: /맞아요, 다음으로/ }).click();
await page.getByText("과실 비율에 영향을 주는 상황을 확인해 주세요").waitFor();
await shot("03-adjustment");
const questions = await page.locator(".md-questions > li").count();
ok("가감 질문이 보임(유형 11: 8개)", questions === 8, String(questions));
ok("쉬운 설명과 '예라면' 안내가 있음", (await page.locator(".md-q-easy").first().textContent()).length > 5 && (await page.getByText(/예라면 →/).first().isVisible()));
// 방향지시등 질문에 '예'
const signal = page.locator(".md-questions > li", { hasText: "방향지시등" }).first();
await signal.locator("label.md-option", { hasText: "예" }).click();
await page.getByRole("button", { name: /결과 보기/ }).click();
await page.waitForURL(/\/analysis\/[0-9a-f-]+$/, { timeout: 30000 });
const analysisId = page.url().split("/").pop();
await page.getByText("과실 분석 결과").first().waitFor();
await page.waitForTimeout(2500); // 비율 산정 연출이 끝나길 기다린다
await shot("04-report");
const reportText = await page.locator("main").innerText();
ok("결과 화면에 비율이 보임", /20/.test(reportText) && /80/.test(reportText), reportText.slice(0, 200));
ok("쉬운 말 제목이 보임", reportText.includes("방향지시등을 켜지 않았거나"));
ok("출발점과 가감 카드가 있음", (await page.locator(".ar-factor-card").count()) === 2);
ok("가짜 문구가 없음 (AV-24901, 46km/h, 99.8%)", !/AV-24901|46km\/h|99\.8%/.test(reportText));

console.log("2) 새로고침해도 같은 결과");
await page.reload();
await page.getByText("과실 분석 결과").first().waitFor();
ok("새로고침 뒤에도 결과 화면", (await page.locator(".ar-factor-card").count()) === 2);

console.log("3) 타임라인");
await page.evaluate(() => { const el = document.querySelector(".ar"); el.scrollTo(0, el.scrollHeight); window.scrollTo(0, document.body.scrollHeight); });
await page.locator(".ar-timeline-link.is-visible").waitFor();
await page.waitForTimeout(500);
await shot("04b-report-bottom");
await page.getByRole("link", { name: /사고 타임라인 바로가기/ }).click();
await page.waitForURL(/\/timeline$/);
await page.locator(".tl-stage").waitFor();
await page.waitForTimeout(800);
await shot("05-timeline");
const timelineText = await page.locator(".tl").innerText();
ok("타임라인 구간이 시간 순으로 보임", (await page.locator(".tl-axis-dot").count()) >= 3, timelineText.slice(0, 200));
ok("충돌 시점 표시", timelineText.includes("충돌 시점"));
ok("속도·G값 같은 가짜 수치 없음", !/TELEMETRY|DECEL|IMPACT FORCE|km\/h|35m|3\.4m/.test(timelineText));
await page.getByRole("button", { name: "다음 시점" }).click();
ok("다음 시점으로 이동", (await page.locator(".tl-now-step").innerText()).includes("STEP 02"));

console.log("4) 유사 판례");
await page.getByRole("link", { name: /유사 판례 바로가기/ }).click();
await page.waitForURL(/\/law$/);
await page.locator(".law-case").first().waitFor();
await shot("06-law");
ok("판례 카드 3건", (await page.locator(".law-case").count()) === 3, String(await page.locator(".law-case").count()));
const lawText = await page.locator(".law-page").innerText();
ok("유사도 퍼센트 없음", !/\d+(\.\d+)?%/.test(lawText.replace(/기본 책임|\d+%\s*:/g, "")), lawText.match(/\d+(\.\d+)?%/)?.[0]);
ok("비교 단계와 검수 표시", lawText.includes("같은 사고 유형") && (lawText.includes("검수됨") || lawText.includes("검수 전")));
await page.locator(".law-case").first().click();
await page.waitForTimeout(400);
await shot("07-law-selected");
ok("선택하면 비슷한 점이 보임", (await page.locator(".law-match-factors li").count()) >= 1);
await page.getByRole("button", { name: /내 사고와 비교하기/ }).click();
await page.locator(".law-modal").waitFor();
await shot("08-law-compare");
ok("공통점·차이점 팝업", (await page.locator(".law-modal-col").count()) === 2 && (await page.locator(".law-modal-col li").count()) >= 2);
await page.keyboard.press("Escape");

console.log("5) 상단 메뉴가 이 분석으로 연결");
await page.getByRole("link", { name: "분석 결과" }).first().click();
await page.waitForURL(new RegExp(`/analysis/${analysisId}$`));
ok("메뉴 '분석 결과'가 방금 분석으로 이동", true);

console.log("6) 지원하지 않는 사고");
await upload("FAKE unsupported 차대보행자\n");
await page.getByText("영상 분석과 외부 AI 서비스 이용 동의").click();
await page.getByText("내 차가 사고에 직접 관여한 영상이에요").click();
await page.getByRole("button", { name: /동의하고 영상 분석 시작하기/ }).click();
await page.getByText("지원하지 않는 사고예요").waitFor({ timeout: 30000 });
await shot("09-unsupported");
ok("차대보행자는 지원하지 않는다고 안내", await page.getByText(/차대보행자 사고는 지원하지 않습니다/).isVisible());

console.log("7) 영상이 너무 길 때");
await upload("FAKE too_long 55\n");
await page.getByText("영상 분석과 외부 AI 서비스 이용 동의").click();
await page.getByText("내 차가 사고에 직접 관여한 영상이에요").click();
await page.getByRole("button", { name: /동의하고 영상 분석 시작하기/ }).click();
await page.getByText("영상이 너무 길어요").waitFor({ timeout: 30000 });
await shot("10-too-long");
ok("길이 안내", await page.getByText(/최대 20초/).first().isVisible());

console.log("8) 유형을 정하지 못할 때");
await upload("FAKE fixture parking\n");
await page.getByText("영상 분석과 외부 AI 서비스 이용 동의").click();
await page.getByText("내 차가 사고에 직접 관여한 영상이에요").click();
await page.getByRole("button", { name: /동의하고 영상 분석 시작하기/ }).click();
await page.getByText("AI가 분석한 사고 상황이 맞나요?").waitFor({ timeout: 30000 });
await shot("11-situation-reference");
ok("AI 가 확신하지 못하면 미리 고르지 않음", (await page.locator("select.md-select").first().inputValue()) === "");
ok("참고 후보가 보임", (await page.locator(".md-chip").count()) >= 1);
await page.getByText("맞는 사고 유형이 없어요").click();
await page.getByRole("button", { name: /결과 보기/ }).click();
await page.waitForURL(/\/analysis\/[0-9a-f-]+$/, { timeout: 30000 });
await page.getByText("가장 가까운 사고 유형").waitFor();
await page.waitForTimeout(500);
await shot("12-unresolved");
const unresolved = await page.locator("main").innerText();
ok("확정 불가: 비율 없이 참고 후보와 안내만", unresolved.includes("확정") || unresolved.includes("안내할 수 없어요"), unresolved.slice(0, 200));

console.log("9) 다른 브라우저에서 열면");
const other = await browser.newContext();
const p2 = await other.newPage();
await p2.goto(`${BASE}/analysis/${analysisId}`);
await p2.getByText("이 브라우저에서 만든 분석이 아니에요").waitFor();
ok("세션이 없으면 안내", true);

ok("브라우저 오류 없음", errors.length === 0, errors.slice(0, 3).join(" | "));
await browser.close();
const failed = results.filter(([, c]) => !c);
console.log(failed.length ? `\n실패 ${failed.length}건` : "\n모두 통과");
process.exit(failed.length ? 1 : 0);
