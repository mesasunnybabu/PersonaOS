// frontend/tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Tell Tailwind which files to scan for class names
  // It only includes CSS for classes you actually use — keeps bundle small
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {},   // We can add custom colors/fonts here later
  },
  plugins: [],
}