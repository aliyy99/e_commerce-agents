/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F8FAFC",
        surface: "#FFFFFF",
        primary: {
          DEFAULT: "#059669",
          hover: "#047857",
          light: "#ECFDF5",
        },
        accent: {
          emerald: "#10B981",
          indigo: "#6366F1",
          amber: "#F59E0B",
          rose: "#F43F5E",
        },
        slate: {
          900: "#0F172A",
          800: "#1E293B",
          700: "#334155",
          600: "#475569",
          500: "#64748B",
          400: "#94A3B8",
          300: "#CBD5E1",
          200: "#E2E8F0",
          100: "#F1F5F9",
          50: "#F8FAFC",
        },
        glass: "rgba(255, 255, 255, 0.7)",
        "glass-border": "rgba(0, 0, 0, 0.05)",
      },
      fontFamily: {
        sans: ['Inter', 'Lato', 'sans-serif'],
        display: ['Poppins', 'Urbanist', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        'premium': '0 10px 40px -10px rgba(0, 0, 0, 0.08)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
