import { stamp } from "../timeFormat";
import TimelineScene from "./TimelineScene";

/* 선택한 시점의 영상 화면. 영상이 없으면 도로 배경과 파일 선택 버튼을 보여 준다 */
export default function VideoPanel({ moment: m, frameColor, source, videoRef, inputRef, videoName, onLoadedMetadata, onLoadFile }) {
  return (
    <div className="tl-video-panel" style={{ "--tl-frame-color": frameColor }}>
      <div className={`tl-player ${m.tone || ""}`}>
        {source ? (
          <video
            ref={videoRef}
            className="tl-video"
            src={source}
            controls
            onLoadedMetadata={onLoadedMetadata}
            aria-label={`${m.label} 블랙박스 영상`}
          />
        ) : (
          <>
            <TimelineScene id={m.id} />
            <div className="tl-player-prompt">
              <p>선택한 시점의 영상</p>
              <button type="button" className="tl-upload" onClick={() => inputRef.current?.click()}>
                블랙박스 영상 선택
              </button>
            </div>
          </>
        )}
        <input
          ref={inputRef}
          className="tl-file-input"
          type="file"
          accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi"
          onChange={onLoadFile}
          aria-label="블랙박스 영상 파일 선택"
        />
        <span className="tl-rec">REC</span>
        <figcaption className="tl-hud tl-mono">
          T: {stamp(m.time)} · {m.hud}
        </figcaption>
      </div>
      {videoName && <p className="tl-video-name">{videoName}</p>}
    </div>
  );
}
