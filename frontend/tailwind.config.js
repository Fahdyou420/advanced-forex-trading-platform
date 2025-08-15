# tailwind.config.js - Tailwind CSS configuration
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'trading-blue': '#60A5FA',
        'trading-green': '#10B981',
        'trading-red': '#EF4444',
        'trading-gray': {
          700: '#374151',
          800: '#1F2937',
          900: '#111827'
        }
      }
    },
  },
  plugins: [],
}
