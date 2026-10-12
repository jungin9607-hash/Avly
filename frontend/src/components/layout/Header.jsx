import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import avlyBrand from "../../assets/avly-brand.png";
import MobileMenu from "./MobileMenu";
import { NAV_ITEMS, getActiveKey } from "../../constants/navItems";
import "./layout.css";

function Header() {
  const { pathname } = useLocation();
  const activeKey = getActiveKey(pathname);
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <div className="site-header-left">
          <Link className="brand" to="/">
            <img className="brand-logo brand-header-logo" src={avlyBrand} alt="에블리 캐릭터와 로고" />
            <div className="brand-text">
              <strong>Avly</strong>
              <span className="brand-korean">에블리</span>
              <span className="brand-divider">|</span>
              <span className="brand-description">AI 교통사고 과실 분석</span>
            </div>
          </Link>

          <nav className="navigation" aria-label="메인 메뉴">
            {NAV_ITEMS.map((item) => {
              const activeClass = item.key === activeKey ? "nav-active" : "";

              if (!item.children) {
                return (
                  <Link key={item.key} className={`nav-item ${activeClass}`} to={item.to}>
                    {item.label}
                  </Link>
                );
              }

              return (
                <div key={item.key} className="nav-item-group">
                  <button type="button" className={`nav-item nav-trigger ${activeClass}`} aria-haspopup="true">
                    {item.label}
                  </button>
                  <div className="mega-menu" aria-label={`${item.label} 메뉴`}>
                    {item.children.map((child) => (
                      <Link
                        key={child.to}
                        to={child.to}
                        className="mega-menu-item"
                        aria-current={child.to === pathname ? "page" : undefined}
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </nav>
        </div>

        <div className="site-header-right">
          <button
            type="button"
            className="mobile-menu-toggle"
            aria-label="메뉴 열기"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>

      {menuOpen && <MobileMenu onClose={() => setMenuOpen(false)} />}
    </header>
  );
}

export default Header;
