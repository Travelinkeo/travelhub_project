/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./core/templates/**/*.html",
    "./core/static/**/*.js"
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "sans-serif"],
        display: ["Space Grotesk", "sans-serif"],
        mono: ['"Geist Mono"', '"Courier New"', "monospace"],
      },
      colors: {
        primary: "var(--primary)",
        brand: "var(--primary)",
        "brand-light": "var(--primary-hover)",
        "primary-hover": "var(--primary-hover)",
        "surface-base": "var(--surface-base)",
        "surface-1": "var(--surface-1)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        "border-color": "var(--border-color)",
        "text-main": "var(--text-main)",
        "text-secondary": "var(--text-secondary)",
        "text-muted": "var(--text-muted)",
        "on-primary": "var(--text-on-primary)",
        "nav-active-bg": "var(--nav-active-bg)",
        "nav-active-border": "var(--nav-active-border)",
        "status-success": "var(--status-success)",
        "status-warning": "var(--status-warning)",
        "status-danger": "var(--status-danger)",
        "status-info": "var(--status-info)",
        "status-success-bg": "var(--status-success-bg)",
        "status-warning-bg": "var(--status-warning-bg)",
        "status-danger-bg": "var(--status-danger-bg)",
        "status-info-bg": "var(--status-info-bg)",
      },
      boxShadow: {
        "inset-custom": "var(--shadow-inset)",
        "btn-custom": "var(--btn-shadow)",
        "card-custom": "var(--card-shadow)",
      },
    },
  },
  plugins: [],
};

