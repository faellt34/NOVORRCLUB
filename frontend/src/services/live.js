import { useEffect, useRef, useState } from "react";

export const useCountUp = (target, { duration = 700 } = {}) => {
  const [value, setValue] = useState(target);
  const [updating, setUpdating] = useState(false);
  const from = useRef(target);
  useEffect(() => {
    if (from.current === target) return;
    const start = from.current, diff = target - start, t0 = performance.now();
    setUpdating(true);
    let raf;
    const step = (now) => {
      const p = Math.min(1, (now - t0) / duration), e = 1 - Math.pow(1 - p, 3);
      setValue(start + diff * e);
      if (p < 1) raf = requestAnimationFrame(step); else from.current = target;
    };
    raf = requestAnimationFrame(step);
    const t = setTimeout(() => setUpdating(false), 900);
    return () => { cancelAnimationFrame(raf); clearTimeout(t); };
  }, [target, duration]);
  return [value, updating];
};

export const useFlash = (ms = 950) => {
  const [flash, setFlash] = useState({});
  const trigger = (key) => {
    setFlash((f) => ({ ...f, [key]: true }));
    setTimeout(() => setFlash((f) => ({ ...f, [key]: false })), ms);
  };
  return [flash, trigger];
};
