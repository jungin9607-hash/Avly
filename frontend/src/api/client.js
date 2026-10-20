import { API_BASE } from "./config.js";

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// 서버가 주는 오류 형식 {"error": {"code", "message"}} 를 ApiError 로 바꾼다. 서버에 닿지 못한 경우도 같은 모양으로 맞춘다.
function toError(status, body) {
  const error = body?.error;
  return new ApiError(status, error?.code ?? "HTTP_ERROR", error?.message ?? "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.", error?.details);
}

async function request(path, { method = "GET", body, sessionId, signal } = {}) {
  const headers = {};
  if (sessionId) headers["X-Session-Id"] = sessionId;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(API_BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, "NETWORK_ERROR", "서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.");
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw toError(response.status, payload);
  return payload;
}

// 영상 업로드는 진행률을 보여 주려고 XMLHttpRequest 를 쓴다.
function upload(path, file, { sessionId, onProgress, signal }) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", API_BASE + path);
    if (sessionId) xhr.setRequestHeader("X-Session-Id", sessionId);
    xhr.upload.onprogress = (event) => event.lengthComputable && onProgress?.(event.loaded / event.total);
    xhr.onload = () => {
      let payload = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        // 본문이 JSON 이 아니면 payload 는 비어 있다
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(payload);
      else reject(toError(xhr.status, payload));
    };
    xhr.onerror = () => reject(new ApiError(0, "NETWORK_ERROR", "서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요."));
    xhr.onabort = () => reject(new DOMException("업로드를 취소했어요.", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export const api = {
  deleteAccident: (accidentId, opts) => request(`/api/v1/accidents/${accidentId}`, { method: "DELETE", ...opts }),
  catalog: (opts) => request("/api/v1/catalog/accident-types", opts),
  createAccident: (title, consent, opts) => request("/api/v1/accidents", { method: "POST", body: { title, consent }, ...opts }),
  uploadVideo: (accidentId, file, opts) => upload(`/api/v1/accidents/${accidentId}/videos`, file, opts),
  startAnalysis: (accidentId, opts) => request(`/api/v1/accidents/${accidentId}/analyses`, { method: "POST", ...opts }),
  getAnalysis: (analysisId, opts) => request(`/api/v1/analyses/${analysisId}`, opts),
  adjustmentQuestions: (analysisId, typeId, role, opts) =>
    request(`/api/v1/analyses/${analysisId}/adjustment-questions?accident_type_id=${typeId}&role=${role}`, opts),
  confirm: (analysisId, body, opts) => request(`/api/v1/analyses/${analysisId}/confirm`, { method: "POST", body, ...opts }),
  videoUrl: async (accidentId, opts) => {
    const info = await request(`/api/v1/accidents/${accidentId}/video-url`, opts);
    return info.available ? API_BASE + info.url : null;
  },
};
