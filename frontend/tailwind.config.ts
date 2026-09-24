import type { Config } from "tailwindcss";

/**
 * "Adaptive Traffic Intelligence" design tokens.
 * Deep graphite base, restrained accent, semantic traffic-state colors.
 * Colors communicate meaning -- never decorative.
 */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#08090b",
          900: "#0d0f12",
          850: "#121418",
          800: "#181b20",
          700: "#22262d",
          600: "#2e333c",
          500: "#3d434e",
        },
        ink: {
          100: "#f4f5f7",
          300: "#c4c9d1",
          500: "#8a919e",
          700: "#5a616d",
        },
        signal: {
          // The single restrained accent -- used sparingly for primary actions
          // and "intelligence" moments (optimization, AI state).
          DEFAULT: "#5eead4",
          dim: "#2dd4bf",
          glow: "rgba(94, 234, 212, 0.18)",
        },
        traffic: {
          normal: "#3fb27f",
          moderate: "#d9a441",
          heavy: "#e07a3f",
          severe: "#d84f4f",
          critical: "#b3245c",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "grid-fine": "linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px)",
      },
      backgroundSize: {
        "grid-fine": "24px 24px",
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.04) inset, 0 12px 32px rgba(0,0,0,0.35)",
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
        lg: "12px",
      },
      keyframes: {
        pulseNode: {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.15)" },
        },
        flowDash: {
          to: { strokeDashoffset: "-24" },
        },
      },
      animation: {
        "pulse-node": "pulseNode 2.4s ease-in-out infinite",
        "flow-dash": "flowDash 1s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
