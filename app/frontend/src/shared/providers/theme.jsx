import { createContext, useContext, useEffect, useState } from "react";

const ThemeCtx = createContext({
  theme: "light",
  toggle: () => {},
});

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState("light");
  useEffect(() => {
    const stored = typeof window !== "undefined" && localStorage.getItem("theme");
    const initial = stored ?? "light";
    setTheme(initial);
  }, []);
  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);
  return (
    <ThemeCtx.Provider
      value={{ theme, toggle: () => setTheme((t) => (t === "light" ? "dark" : "light")) }}
    >
      {children}
    </ThemeCtx.Provider>
  );
}

export const useTheme = () => useContext(ThemeCtx);
