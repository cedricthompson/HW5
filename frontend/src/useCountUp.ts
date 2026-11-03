import { useEffect, useRef, useState } from "react";

/** Animates a number from its last value to `target` (used for the cash balance). */
export function useCountUp(target: number | null, ms = 1100): number | null {
  const [value, setValue] = useState<number | null>(target);
  const from = useRef<number | null>(target);

  useEffect(() => {
    if (target == null) return;
    const start = from.current ?? target;
    if (start === target) {
      setValue(target);
      return;
    }
    const t0 = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(start + (target - start) * eased);
      if (p < 1) frame = requestAnimationFrame(tick);
      else from.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      from.current = target;
    };
  }, [target, ms]);

  return value;
}
