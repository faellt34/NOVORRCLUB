import { useEffect, useRef } from "react";

export const GlobeCanvas = ({ color = "255,255,255" }) => {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current, ctx = canvas.getContext("2d");
    let raf, w, h, t = 0;
    const N = 2600, pts = [];
    const noise = (x, y, z) => Math.sin(x * 3.1 + y * 1.7) * Math.cos(z * 2.9 - x * 1.3) + Math.sin((x + z) * 5.3) * 0.5 + Math.cos(y * 4.7 + z * 2.1) * 0.6;
    for (let i = 0; i < N * 2; i++) {
      const y = 1 - (i / (N * 2 - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * 2.399963;
      const p = [r * Math.cos(th), y, r * Math.sin(th)];
      if (noise(...p) > -0.15 || (i % 5 === 0)) pts.push(p);
    }
    const links = Array.from({ length: 18 }, () => [Math.floor(Math.random() * pts.length), Math.floor(Math.random() * pts.length), Math.random() * 6]);
    const resize = () => { w = canvas.width = canvas.offsetWidth * 2; h = canvas.height = canvas.offsetHeight * 2; };
    resize(); window.addEventListener("resize", resize);
    const proj = (p, rot) => {
      const x = p[0] * Math.cos(rot) - p[2] * Math.sin(rot), z = p[0] * Math.sin(rot) + p[2] * Math.cos(rot);
      const R = Math.min(w, h) * 0.46, s = 1 / (1.8 - z * 0.55);
      return [w * 0.64 + x * R * s, h * 0.52 + p[1] * R * s, z, s];
    };
    const draw = () => {
      t += 0.0035; ctx.clearRect(0, 0, w, h);
      for (const p of pts) {
        const [x, y, z, s] = proj(p, t);
        if (z < -0.05) continue;
        const a = Math.min(1, 0.35 + z * 0.75), sz = 3.6 * s;
        ctx.fillStyle = `rgba(${color},${a})`; ctx.fillRect(x - sz / 2, y - sz / 2, sz, sz);
      }
      for (const l of links) {
        const [ax, ay, az] = proj(pts[l[0]], t), [bx, by, bz] = proj(pts[l[1]], t);
        if (az < 0 || bz < 0) continue;
        const ph = (t * 12 + l[2]) % 6, k = Math.min(1, ph / 3), fade = ph > 3 ? 1 - (ph - 3) / 3 : 1;
        const mx = (ax + bx) / 2 + (ay - by) * 0.25, my = (ay + by) / 2 - Math.abs(ax - bx) * 0.25;
        ctx.strokeStyle = `rgba(255,255,255,${0.9 * fade})`; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(ax, ay);
        const steps = 30;
        for (let i = 1; i <= steps * k; i++) { const u = i / steps; ctx.lineTo((1 - u) ** 2 * ax + 2 * (1 - u) * u * mx + u ** 2 * bx, (1 - u) ** 2 * ay + 2 * (1 - u) * u * my + u ** 2 * by); }
        ctx.stroke();
        ctx.fillStyle = `rgba(255,255,255,${fade})`; ctx.beginPath(); ctx.arc(ax, ay, 4, 0, 7); ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, [color]);
  return <canvas ref={ref} data-testid="globe-canvas" className="absolute inset-0 w-full h-full pointer-events-none" />;
};
