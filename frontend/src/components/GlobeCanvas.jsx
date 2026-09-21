import { useEffect, useRef } from "react";

const toXYZ = (lat, lon) => {
  const la = (lat * Math.PI) / 180, lo = (lon * Math.PI) / 180;
  return [Math.cos(la) * Math.cos(lo), -Math.sin(la), Math.cos(la) * Math.sin(lo)];
};

export const GlobeCanvas = ({ color = "255,255,255", cities = [], interactive = true, onHover }) => {
  const ref = useRef(null);
  const citiesRef = useRef(cities);
  citiesRef.current = cities;
  useEffect(() => {
    const canvas = ref.current, ctx = canvas.getContext("2d");
    let raf, w, h, t = 0, speed = 0.0035, tilt = 0, targetTilt = 0, mouse = null;
    const N = 9000, pts = [];
    const noise = (x, y, z) => Math.sin(x * 3.1 + y * 1.7) * Math.cos(z * 2.9 - x * 1.3) + Math.sin((x + z) * 5.3) * 0.5 + Math.cos(y * 4.7 + z * 2.1) * 0.6;
    for (let i = 0; i < N * 2; i++) {
      const y = 1 - (i / (N * 2 - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * 2.399963;
      const j = () => (Math.random() - 0.5) * 0.035;
      const p = [r * Math.cos(th) + j(), y + j(), r * Math.sin(th) + j()];
      const nv = noise(...p);
      if (nv > 0.15 || (nv > -0.4 && i % 3 === 0) || i % 9 === 0) pts.push(p);
    }
    const links = Array.from({ length: 22 }, () => [Math.floor(Math.random() * pts.length), Math.floor(Math.random() * pts.length), Math.random() * 6]);
    const resize = () => { w = canvas.width = canvas.offsetWidth * 2; h = canvas.height = canvas.offsetHeight * 2; };
    resize(); window.addEventListener("resize", resize);
    const parent = canvas.parentElement;
    const onMove = (e) => {
      const r = parent.getBoundingClientRect();
      mouse = [((e.clientX - r.left) / r.width) * 2, ((e.clientY - r.top) / r.height) * 2];
      const nx = (e.clientX - r.left) / r.width - 0.5;
      speed = 0.0035 + nx * 0.008;
      targetTilt = ((e.clientY - r.top) / r.height - 0.5) * 0.6;
    };
    const onLeave = () => { mouse = null; speed = 0.0035; targetTilt = 0; onHover?.(null); };
    if (interactive) { parent.addEventListener("mousemove", onMove); parent.addEventListener("mouseleave", onLeave); }
    const proj = (p) => {
      const x0 = p[0] * Math.cos(t) - p[2] * Math.sin(t), z0 = p[0] * Math.sin(t) + p[2] * Math.cos(t);
      const y = p[1] * Math.cos(tilt) - z0 * Math.sin(tilt), z = p[1] * Math.sin(tilt) + z0 * Math.cos(tilt);
      const portrait = h > w;
      const R = Math.min(w, h) * (portrait ? 0.9 : 0.62), s = 1 / (1.7 - z * 0.45);
      return [w * (portrait ? 0.5 : 0.72) + x0 * R * s, h * (portrait ? 0.42 : 0.5) + y * R * s, z, s];
    };
    const draw = () => {
      t += speed; tilt += (targetTilt - tilt) * 0.05; ctx.clearRect(0, 0, w, h);
      for (const p of pts) {
        const [x, y, z, s] = proj(p);
        if (z < -0.05) continue;
        const a = Math.min(1, 0.45 + z * 0.7), sz = 3.4 * s;
        ctx.fillStyle = `rgba(${color},${a})`; ctx.fillRect(x - sz / 2, y - sz / 2, sz, sz);
      }
      for (const l of links) {
        const [ax, ay, az] = proj(pts[l[0]]), [bx, by, bz] = proj(pts[l[1]]);
        if (az < 0 || bz < 0) continue;
        const ph = (t * 12 + l[2]) % 6, k = Math.min(1, ph / 3), fade = ph > 3 ? 1 - (ph - 3) / 3 : 1;
        const mx = (ax + bx) / 2 + (ay - by) * 0.25, my = (ay + by) / 2 - Math.abs(ax - bx) * 0.25;
        ctx.strokeStyle = `rgba(255,255,255,${0.95 * fade})`; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(ax, ay);
        for (let i = 1; i <= 30 * k; i++) { const u = i / 30; ctx.lineTo((1 - u) ** 2 * ax + 2 * (1 - u) * u * mx + u ** 2 * bx, (1 - u) ** 2 * ay + 2 * (1 - u) * u * my + u ** 2 * by); }
        ctx.stroke(); ctx.fillStyle = `rgba(255,255,255,${fade})`; ctx.beginPath(); ctx.arc(ax, ay, 4, 0, 7); ctx.fill();
      }
      let hovered = null;
      for (const c of citiesRef.current) {
        const [x, y, z, s] = proj(toXYZ(c.lat, c.lon));
        if (z < 0.05) continue;
        const pulse = 6 + Math.sin(t * 40 + c.lat) * 2;
        const near = mouse && Math.hypot(mouse[0] * w / 2 - x, mouse[1] * h / 2 - y) < 40;
        if (near) hovered = c;
        ctx.fillStyle = "rgba(251,191,36,0.35)"; ctx.beginPath(); ctx.arc(x, y, pulse * 2 * s, 0, 7); ctx.fill();
        ctx.fillStyle = near ? "#fff" : "#FBBF24"; ctx.beginPath(); ctx.arc(x, y, pulse * s, 0, 7); ctx.fill();
        ctx.font = `${near ? "bold " : ""}${Math.round(22 * s)}px sans-serif`; ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.fillText(`${c.name}${c.partners ? ` · ${c.partners}` : ""}`, x + 14, y - 10);
      }
      onHover?.(hovered);
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); if (interactive) { parent.removeEventListener("mousemove", onMove); parent.removeEventListener("mouseleave", onLeave); } };
  }, [color, interactive, onHover]);
  return <canvas ref={ref} data-testid="globe-canvas" className="absolute inset-0 w-full h-full pointer-events-none" />;
};
