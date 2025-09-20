/**** Tailwind Config ****/
const defaultTheme = require('tailwindcss/defaultTheme');

module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#0D1E40',       // Azul Oscuro
          secondary: '#2173A6',     // Azul Medio
          accent: '#03A6A6',        // Turquesa
          highlight: '#F2CC0C',     // Amarillo
          danger: '#D92B2B',         // Rojo
          'on-primary': '#FFFFFF',   // Texto sobre primario
          'on-accent': '#FFFFFF',    // Texto sobre acento
        }
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans]
      }
    }
  },
  plugins: [],
};
