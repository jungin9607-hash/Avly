import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import avlyMascot from "../../assets/avly-mascot.png";
import Icon from "../ui/Icon";
import { NAV_ITEMS, getActiveKey } from "../../constants/navItems";

function MobileMenu({ onClose }) {
  const { pathname } = useLocation();
  const activeKey = getActiveKey(pathname);
  const [analysisOpen, setAnalysisOpen] = useState(true);

  return (
    <div className="mobile-menu-overlay" onClick={onClose}>
      <aside
        className="mobile-menu-panel"
        role="menu"
        aria-label="모바일 메뉴"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mobile-menu-header">
          <Link to="/" className="mobile-menu-brand">
            <img className="brand-logo" src={avlyMascot} alt="" />
            <span><strong>Avly</strong> <small>교통사고 AI 분석</small></span>
          </Link>
          <button type="button" className="mobile-menu-close" aria-label="메뉴 닫기" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>

        <nav className="mobile-menu-list">
          {NAV_ITEMS.map((item) => {
            const isActive = item.key === activeKey;

            if (!item.children) {
              return (
                <Link
                  key={item.key}
                  to={item.to}
                  className={`mobile-menu-item ${isActive ? "active" : ""}`}
                  onClick={onClose}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  {isActive && <small className="mobile-menu-current">현재 화면</small>}
                </Link>
              );
            }

            return (
              <div key={item.key}>
                <div className="mobile-menu-analysis-row">
                  <button
                    type="button"
                    className={`mobile-menu-item mobile-menu-analysis ${isActive ? "active" : ""}`}
                    aria-expanded={analysisOpen}
                    aria-controls="mobile-analysis-submenu"
                    onClick={() => setAnalysisOpen((open) => !open)}
                  >
                    <Icon name={item.icon} />
                    <span>{item.label}</span>
                    <Icon name="expand_more" />
                  </button>
                </div>

                {analysisOpen && (
                  <div className="mobile-submenu" id="mobile-analysis-submenu">
                    {item.children.map((child) => (
                      <Link
                        key={child.to}
                        to={child.to}
                        aria-current={child.to === pathname ? "page" : undefined}
                        onClick={onClose}
                      >
                        <span>{child.label}</span>
                        {child.to === pathname ? (
                          <small className="mobile-menu-current">현재 화면</small>
                        ) : (
                          <small>보기 &gt;</small>
                        )}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </aside>
    </div>
  );
}

export default MobileMenu;
