import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export const useHashScroll = (ready) => {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash || !ready) return;
    const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    return () => clearTimeout(t);
  }, [hash, ready]);
};
