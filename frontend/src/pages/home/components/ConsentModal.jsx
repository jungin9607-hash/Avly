import { useState } from "react";
import ModalShell from "./ModalShell";

// ⚠️ 동의 문구는 초안이다. 서비스에 올리기 전에 법무 검토로 확정하고, 바꾸면 api/config.js 의 CONSENT_VERSION 도 함께 바꾼다.
//   - 영상 일부 장면(이미지)이 외부 AI 서비스로 전송된다는 사실을 밝혀야 한다 (국외 이전에 해당할 수 있음)
//   - 자동으로 가리는 방식은 완전하지 않다는 점을 알려야 한다
const ANALYSIS = {
  title: "영상 분석과 외부 AI 서비스 이용 동의",
  body: "올린 영상에서 번호판과 사람을 자동으로 가린 뒤, 그 영상의 일부 장면(이미지)을 외부 AI 서비스로 보내 사고 상황을 분석합니다. 자동으로 가리는 방식은 완전하지 않아서 일부가 가려지지 않을 수 있어요. 분석 결과는 손해보험협회 과실비율 인정기준과 판례 자료를 참고한 안내이며 법적 효력이 없습니다. 올린 원본 영상은 이용을 시작한 지 2시간이 지나면 자동으로 삭제하고, 아래 저장 동의를 하지 않으시면 분석 결과도 같은 때 삭제합니다. 화면의 '결과 지우기'로 바로 지울 수도 있어요. 차대차 사고가 아니어서 분석하지 못한 영상은 저장에 동의하셨더라도 하루 안에 삭제합니다.",
};
// 동의가 아니라 영상 조건 확인이다. 이 서비스는 블랙박스 차량이 사고 당사자인 영상만 분석한다(목격 영상은 분석하지 못한다).
const INVOLVED = {
  title: "내 차가 사고에 직접 관여한 영상이에요",
  body: "블랙박스를 단 내 차가 사고 당사자(접촉했거나 사고 상황의 한쪽)인 영상만 분석할 수 있어요. 다른 차들의 사고를 지나가며 목격한 영상은 분석하지 못해요.",
};
// 사고가 난 장소 종류. 고르면 그 장소의 사고 유형만 비교해서 더 정확해진다. 모르겠으면 비워 둬도 된다.
// 값은 과실표의 장소 이름(서버가 같은 이름으로 받는다), 글자는 확인 화면의 1번 "사고 장소"와 같은 쉬운 말이다.
const PLACES = [
  ["사거리 교차로(신호등 있음)", "신호등 있는 사거리"],
  ["사거리 교차로(신호등 없음)", "신호등 없는 사거리"],
  ["T자형 교차로", "T자 삼거리"],
  ["직선 도로", "직선 도로"],
  ["회전교차로", "회전교차로(로터리)"],
  ["주차장(또는 차도가 아닌 장소)", "주차장 등 도로가 아닌 곳"],
  ["차도와 차도가 아닌 장소", "도로와 도로 밖(주차장·건물 앞 등)을 드나드는 곳"],
];
const RETENTION = {
  title: "영상 저장과 서비스 개선 활용 동의",
  body: "번호판과 사람을 가린 영상과 분석 결과(AI가 분석한 내용과 직접 확인·수정한 사고 상황, 답변)를 90일 동안 저장하고, 서비스를 개선하고 새 기능을 만드는 데 활용하는 것에 동의합니다. 보관 기간이 지나면 삭제하며, 저장한 내용을 화면에서 다시 보여 드리지는 않아요. 이용 중에는 '결과 지우기'로 언제든 바로 삭제할 수 있어요. 동의하지 않아도 분석은 이용할 수 있으며, 이 경우 가린 영상과 분석 결과도 이용 2시간 뒤 삭제됩니다.",
};

/* 1단계: 영상 수집 동의
 * 분석 동의와 당사자 영상 확인(필수)이 있어야 분석을 시작할 수 있고, 저장 동의(선택)는 하지 않아도 된다. */
export default function ConsentModal({ fileName, onStart, onClose, onPickAnother }) {
  const [analysis, setAnalysis] = useState(false);
  const [involved, setInvolved] = useState(false);
  const [retention, setRetention] = useState(false);
  const [place, setPlace] = useState("");
  // 전체 동의: 아래 세 항목을 한꺼번에 켜고 끈다. 항목은 각각 따로 바꿀 수 있고, 모두 켜져 있을 때만 전체 동의가 켜진다.
  const all = analysis && involved && retention;
  const setAll = (value) => {
    setAnalysis(value);
    setInvolved(value);
    setRetention(value);
  };

  return (
    <ModalShell title="블랙박스 영상 수집 동의" progress={[1, 4]} onClose={onClose}>
      <div className="md-body">
        {fileName && (
          <p className="md-file">
            <IconVideo />
            <span>{fileName}</span>
          </p>
        )}

        <div className="md-place">
          <label htmlFor="md-place-select">사고가 난 장소 <small>(선택) 알면 더 정확하게 분석해요</small></label>
          <select id="md-place-select" value={place} onChange={(e) => setPlace(e.target.value)}>
            <option value="">잘 모르겠어요</option>
            {PLACES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <label className={all ? "md-all md-all-top is-on" : "md-all md-all-top"}>
          <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} />
          <span className="md-check" aria-hidden="true" />
          <span>
            전체 동의 <small>필수와 선택 항목을 모두 포함해요</small>
          </span>
        </label>

        <ul className="md-items md-consent-list">
          <li>
            <Consent checked={analysis} onChange={setAnalysis} required item={ANALYSIS} />
          </li>
          <li>
            <Consent checked={involved} onChange={setInvolved} required item={INVOLVED} />
          </li>
          <li>
            <Consent checked={retention} onChange={setRetention} item={RETENTION} />
          </li>
        </ul>
      </div>

      <footer className="md-foot">
        <button type="button" className="md-btn md-btn-wide" disabled={!analysis || !involved} onClick={() => onStart({ retention, place: place || null })}>
          동의하고 영상 분석 시작하기
          <span aria-hidden="true">→</span>
        </button>
        <div className="md-foot-row md-foot-sub">
          <button type="button" className="md-btn-ghost" onClick={onPickAnother}>
            다른 영상 선택
          </button>
          <button type="button" className="md-btn-ghost" onClick={onClose}>
            취소
          </button>
        </div>
      </footer>
    </ModalShell>
  );
}

function Consent({ checked, onChange, required = false, item }) {
  return (
    <label className={checked ? "md-all md-consent is-on" : "md-all md-consent"}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="md-check" aria-hidden="true" />
      <span className="md-item-text">
        <span className="md-item-title">
          <em>{required ? "필수" : "선택"}</em>
          {item.title}
        </span>
        <span className="md-item-body">{item.body}</span>
      </span>
    </label>
  );
}

const IconVideo = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3" y="6" width="13" height="12" rx="2" />
    <path d="m16 10 5-3v10l-5-3" />
  </svg>
);
