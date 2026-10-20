// 서버 주소. 개발에서는 frontend/.env 의 VITE_API_BASE 로 바꿀 수 있다 (기본 http://localhost:8000).
export const API_BASE = (import.meta.env?.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

// 사용자가 본 동의 문서의 버전. 동의 문구를 바꾸면 이 값도 바꾼다.
export const CONSENT_VERSION = "2026-10-20.2";

// 영상 길이 안내 (서버가 20초를 넘으면 분석하지 않는다)
export const MAX_VIDEO_SECONDS = 20;
