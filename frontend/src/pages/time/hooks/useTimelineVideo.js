import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/client";

/* 타임라인에 보여 줄 영상. 서버에 보관된 비식별 영상이 있으면 그것을, 없으면 사용자가 직접 고른 영상을 쓴다 */
export default function useTimelineVideo(session) {
  const videoRef = useRef(null);
  const inputRef = useRef(null);
  const [videoUrl, setVideoUrl] = useState(""); // 사용자가 직접 고른 영상(영상을 보관하지 않은 경우의 대안)
  const [videoName, setVideoName] = useState("");
  const [serverVideo, setServerVideo] = useState(null); // 번호판·사람을 가린 영상 (보관 동의한 경우)

  // 서명 주소는 짧게 유효하므로 화면에 들어올 때 받는다.
  useEffect(() => {
    let cancelled = false;
    api.videoUrl(session.accidentId, { sessionId: session.sessionId }).then(
      (url) => !cancelled && setServerVideo(url),
      () => {},
    );
    return () => {
      cancelled = true;
    };
  }, [session.accidentId, session.sessionId]);

  useEffect(() => {
    if (!videoUrl) return undefined;
    return () => URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);

  const seek = (time) => {
    const video = videoRef.current;
    if (video && video.readyState >= HTMLMediaElement.HAVE_METADATA && Number.isFinite(video.duration)) {
      video.currentTime = Math.min(time, Math.max(0, video.duration - 0.05));
    }
  };

  const loadVideo = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setVideoUrl(URL.createObjectURL(file));
    setVideoName(file.name);
    event.target.value = "";
  };

  return { videoRef, inputRef, source: videoUrl || serverVideo, videoName, seek, loadVideo };
}
