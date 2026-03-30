/** @type {import('tailwindcss').Config} */
export default {
  // 在 content 数组中补充 "./app.html"
  content: ["./index.html", "./app.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}