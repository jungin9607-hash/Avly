import CaseBasisNotice from "../../common/components/CaseBasisNotice";

// 홈 화면 하단 주의 문구와 같은 문구를 보여 준다. (서버가 보내는 보고서용 문구는 PDF 보고서에서만 쓴다)
export default function ReportNotice() {
  return <CaseBasisNotice className="ar-notice" />;
}
