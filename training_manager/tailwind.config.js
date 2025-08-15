/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./**/templates/**/*.html",
    "./dashboard/static/**/*.js",
  ],
  theme: {
    container: { center: true, padding: '1rem' },
    extend: {
      colors: {
        brand: {
          50:'#eef6ff',100:'#d9e9ff',200:'#b6d3ff',300:'#86b4ff',
          400:'#5492ff',500:'#2f74ff',600:'#1b59e0',700:'#1748b6',
          800:'#143d94',900:'#0f2e6e'
        }
      },
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,.08)',
        focus: '0 0 0 3px rgba(47,116,255,.35)'
      },
      borderRadius: { xl: '1rem', '2xl': '1.25rem' }
    }
  },
  plugins: [],
}
