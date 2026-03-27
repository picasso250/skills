/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./public/index.html", "./src/**/*.js"],
  theme: {
    extend: {
      colors: {
        background: "#f7f9fb",
        surface: "#ffffff",
        "surface-soft": "#f0f4f7",
        "surface-strong": "#e1e9ee",
        text: "#2a3439",
        muted: "#566166",
        primary: "#2d50d9",
        "primary-text": "#f9f6ff",
      },
      boxShadow: {
        editorial: "0 12px 32px rgba(42, 52, 57, 0.04)",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        headline: ["Manrope", "sans-serif"],
      },
      maxWidth: {
        chat: "820px",
      },
    },
  },
  plugins: [],
};

