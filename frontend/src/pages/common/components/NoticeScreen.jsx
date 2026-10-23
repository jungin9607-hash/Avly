import { Link } from "react-router-dom";
import { ROUTES } from "../../../routes";
import TopNav from "./TopNav";
import "./NoticeScreen.css";

// 결과를 보여 줄 수 없을 때 쓰는 안내 화면 (분석 없음 · 불러오는 중 · 삭제됨 등)
// notice: { title, body?, retry?, link?: { to, label }, analyzing? }
// analyzing(분석 중)이면 문구 없이 배경만 보여 준다. 화면 읽기 프로그램에는 제목만 알린다. (나중에 로딩바가 들어갈 자리)
export default function NoticeScreen({ active, notice, onRetry }) {
  if (notice.analyzing) {
    return (
      <div className="ns">
        <TopNav active={active} theme="dark" />
        <main className="ns-main" role="status">
          <h1 className="ns-sr-only">{notice.title}</h1>
        </main>
      </div>
    );
  }
  return (
    <div className="ns">
      <TopNav active={active} theme="dark" />
      <main className="ns-main" role="status">
        <h1>{notice.title}</h1>
        {notice.body && <p>{notice.body}</p>}
        <div className="ns-actions">
          {notice.retry && (
            <button type="button" className="ns-button" onClick={onRetry}>
              다시 불러오기
            </button>
          )}
          {notice.link && (
            <Link className="ns-button" to={notice.link.to}>
              {notice.link.label}
            </Link>
          )}
          {notice.link?.to !== ROUTES.home && (
            <Link className="ns-link" to={ROUTES.home}>
              새 영상 분석하기
            </Link>
          )}
        </div>
      </main>
    </div>
  );
}
