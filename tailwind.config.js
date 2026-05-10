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
        },
        slate: {
          900: "#0F172A",
          500: "#64748B",
          200: "#E2E8F0",
        },
        glass: "rgba(255, 255, 255, 0.8)",
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
  plugins: [],
}
