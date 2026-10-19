import { useState } from "react";
import ModalShell from "./ModalShell";

// ⚠️ 동의 문구는 초안이다. 서비스에 올리기 전에 법무 검토로 확정하고, 바꾸면 api/config.js 의 CONSENT_VERSION 도 함께 바꾼다.
//   - 영상 일부 장면(이미지)이 외부 AI 서비스로 전송된다는 사실을 밝혀야 한다 (국외 이전에 해당할 수 있음)
//   - 자동으로 가리는 방식은 완전하지 않다는 점을 알려야 한다
const ANALYSIS = {
  title: "영상 분석과 외부 AI 서비스 이용 동의",
  body: "올린 영상에서 번호판과 사람을 자동으로 가린 뒤, 그 영상의 일부 장면(이미지)을 외부 AI 서비스로 보내 사고 상황을 분석합니다. 자동으로 가리는 방식은 완전하지 않아서 일부가 가려지지 않을 수 있어요. 분석 결과는 손해보험협회 과실비율 인정기준과 판례 자료를 참고한 안내이며 법적 효력이 없습니다. 올린 원본 영상은 이용이 끝나면 삭제하고, 차대차 사고가 아니어서 분석하지 못한 영상은 저장에 동의하셨더라도 하루 뒤 삭제합니다.",
};
// 동의가 아니라 영상 조건 확인이다. 이 서비스는 블랙박스 차량이 사고 당사자인 영상만 분석한다(목격 영상은 분석하지 못한다).
const INVOLVED = {
  title: "내 차가 사고에 직접 관여한 영상이에요",
  body: "블랙박스를 단 내 차가 사고 당사자(접촉했거나 사고 상황의 한쪽)인 영상만 분석할 수 있어요. 다른 차들의 사고를 지나가며 목격한 영상은 분석하지 못해요.",
};
const RETENTION = {
  title: "영상 저장과 서비스 개선 활용 동의",
  body: "번호판과 사람을 가린 영상을 서비스에 저장하고, 분석 결과를 다시 확인하거나 서비스를 개선하고 새 기능을 만드는 데 활용하는 것에 동의합니다. 동의하지 않아도 분석은 이용할 수 있으며, 이 경우 영상은 이용이 끝나면 삭제됩니다.",
};

/* 1단계: 영상 수집 동의
 * 분석 동의와 당사자 영상 확인(필수)이 있어야 분석을 시작할 수 있고, 저장 동의(선택)는 하지 않아도 된다. */
export default function ConsentModal({ fileName, onStart, onClose, onPickAnother }) {
  const [analysis, setAnalysis] = useState(false);
  const [involved, setInvolved] = useState(false);
  const [retention, setRetention] = useState(false);

  return (
    <ModalShell title="블랙박스 영상 수집 동의" progress={[1, 4]} onClose={onClose}>
      <div className="md-body">
        {fileName && (
          <p className="md-file">
            <IconVideo />
            <span>{fileName}</span>
          </p>
        )}

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
        <button type="button" className="md-btn md-btn-wide" disabled={!analysis || !involved} onClick={() => onStart({ retention })}>
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
