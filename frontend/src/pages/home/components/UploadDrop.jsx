import { useState } from "react";
import { IconPlus, IconUpload } from "./icons";

/* 영상 끌어다 놓기 · 파일 선택. 고른 파일 목록은 onFiles 로 넘기고, 검사와 오류 문구는 부모가 정한다 */
export default function UploadDrop({ inputRef, error, maxMb, onFiles }) {
  const [dragging, setDragging] = useState(false);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    onFiles(e.dataTransfer.files);
  };

  const onDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
  };

  return (
    <section
      className={dragging ? "uh-drop is-over" : "uh-drop"}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="uh-drop-icon">
        <IconUpload />
      </div>
      <h2>블랙박스 동영상 파일을 이곳에 끌어다 놓으세요</h2>
      <button type="button" className="uh-btn uh-btn-solid" onClick={() => inputRef.current.click()}>
        <IconPlus />
        블랙박스 영상 업로드
      </button>
      <p className="uh-drop-hint">MP4, MOV, AVI 지원 · 단일 파일 최대 {maxMb}MB 이내 권장</p>
      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
        hidden
        onChange={(e) => {
          onFiles(e.target.files);
          e.target.value = "";
        }}
      />
      {error && (
        <p className="uh-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
