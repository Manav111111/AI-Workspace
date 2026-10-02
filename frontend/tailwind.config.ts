


import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050505",
        foreground: "#F5F5F5",
        // Enterprise Black & Orange Palette
        surface: {
          50: "#222222",
          100: "#1A1A1A", // subtle hover background
          200: "#151515", // elevated surfaces
          300: "#101010", // card background
          400: "#0B0B0B", // secondary background
          500: "#050505", // main background
          600: "#1A1A1A",
          700: "#151515",
          800: "#101010",
          900: "#0B0B0B",
          950: "#050505",
          border: "#262626",
          borderLight: "#383838",
          borderSubtle: "#1C1C1C",
        },
        orange: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#FFC247", // Orange highlight
          500: "#FF9D00", // Primary accent orange
          600: "#FF6A00", // Secondary orange
          700: "#ea580c",
          800: "#9a3412",
          900: "#431407",
          950: "#220902",
        },
        // Forest / Emerald kept strictly for semantic success / health status
        forest: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#FF9D00",
          500: "#FF9D00",
          600: "#FF6A00",
          700: "#ea580c",
          800: "#431407",
          900: "#2a1205",
          950: "#180a03",
        },
        sand: {
          50: "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
          950: "#09090b",
        },
        amber: {
          50: "#fffbeb",
          100: "#fef3c7",
          200: "#fde68a",
          300: "#fcd34d",
          400: "#FFC247",
          500: "#FF9D00",
          600: "#FF6A00",
          700: "#ea580c",
          800: "#9a3412",
          900: "#431407",
          950: "#220902",
        },
        text: {
          primary: "#F5F5F5",
          secondary: "#A1A1AA",
          muted: "#737373",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-body)",
          "DM Sans",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        body: [
          "var(--font-body)",
          "DM Sans",
          "sans-serif",
        ],
        display: [
          "var(--font-display)",
          "Syne",
          "sans-serif",
        ],
        heading: [
          "var(--font-display)",
          "Syne",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "JetBrains Mono",
          "Fira Code",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.6)",
        card: "0 4px 20px -2px rgba(0, 0, 0, 0.7)",
        orange: "0 4px 20px -2px rgba(255, 157, 0, 0.25)",
        "orange-sm": "0 2px 10px -1px rgba(255, 157, 0, 0.2)",
        forest: "0 4px 20px -2px rgba(255, 157, 0, 0.25)",
        amber: "0 4px 20px -2px rgba(255, 157, 0, 0.25)",
      },
    },
  },
  plugins: [],
};
export default config;

