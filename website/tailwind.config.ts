import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0A0A",
        surface: "#111111",
        accent: "#F59E0B",
        "accent-light": "#FBBF24",
        forget: "#EF4444",
        dim: "#141414",
        cyan: "#22D3EE",
      },
      fontFamily: {
        display: ["'Fraunces'", "Georgia", "serif"],
        body: ["'Instrument Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "Menlo", "monospace"],
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        blink: "blink 1s step-end infinite",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
