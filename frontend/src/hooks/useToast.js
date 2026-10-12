import { useCallback, useEffect, useRef, useState } from "react";

export function useToast(duration = 3000) {
  const [toast, setToast] = useState("");
  const timerRef = useRef(null);

  const showToast = useCallback(
    (message) => {
      clearTimeout(timerRef.current);
      setToast(message);
      timerRef.current = setTimeout(() => setToast(""), duration);
    },
    [duration]
  );

  useEffect(() => () => clearTimeout(timerRef.current), []);

  return { toast, showToast };
}
