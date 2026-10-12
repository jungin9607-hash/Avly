import Icon from "../ui/Icon";
import "./layout.css";

const DEFAULT_NOTICE =
  "본 서비스는 AI 영상 분석 및 과실비율 인정기준·판례 데이터를 기반으로 제공되는 참고자료이며, 확정 판결을 대신하지 않습니다.";

function Footer({ notice = DEFAULT_NOTICE, onGuidelineClick }) {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-notice">
          <Icon name="verified_user" />
          <div>
            <strong>법적 책임 고지 및 안내</strong>
            <p>{notice}</p>
          </div>
          {onGuidelineClick && (
            <button type="button" onClick={onGuidelineClick}>
              판례 기준 가이드라인
            </button>
          )}
        </div>

        <div className="site-footer-bottom">
          <div>
            <strong>Avly</strong> (에블리)
            <span> · </span>
            <a href="#">이용약관</a>
            <span> · </span>
            <a href="#">개인정보처리방침</a>
            <span> · </span>
            <a href="#">고객지원센터</a>
          </div>
          <span>© {new Date().getFullYear()} Avly Inc. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
