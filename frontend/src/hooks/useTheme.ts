import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
type ThemePreference = Theme | "system";

export const THEME_STORAGE_KEY = "agro-ai-pro.theme";

function systemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function savedPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  return saved === "light" || saved === "dark" ? saved : "system";
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(savedPreference);
  const [systemValue, setSystemValue] = useState<Theme>(systemTheme);
  const theme = preference === "system" ? systemValue : preference;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSystemValue(media.matches ? "dark" : "light");
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setPreference((current) => {
      const resolved = current === "system" ? systemTheme() : current;
      const next: Theme = resolved === "dark" ? "light" : "dark";
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
      return next;
    });
  }, []);

  return { theme, preference, toggleTheme };
}
