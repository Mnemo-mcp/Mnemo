import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Georgia', 'Times New Roman', 'serif'],
        body: ['system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
      colors: {
        'surface': 'oklch(0.13 0.01 60)',
        'surface-raised': 'oklch(0.16 0.012 60)',
        'surface-overlay': 'oklch(0.19 0.014 60)',
        'accent': 'oklch(0.72 0.14 55)',
        'accent-dim': 'oklch(0.55 0.10 55)',
        'accent-bright': 'oklch(0.82 0.12 55)',
        'text-primary': 'oklch(0.93 0.008 60)',
        'text-secondary': 'oklch(0.65 0.01 60)',
        'text-muted': 'oklch(0.45 0.008 60)',
        'border': 'oklch(0.25 0.01 60)',
        'border-subtle': 'oklch(0.20 0.008 60)',
      },
      animation: {
        'enter': 'enter 0.45s ease-out forwards',
        'enter-delayed': 'enter 0.45s ease-out 0.1s forwards',
      },
      keyframes: {
        enter: {
          '0%': { opacity: '0', transform: 'translateY(8px)', filter: 'blur(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)', filter: 'blur(0px)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
