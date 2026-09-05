/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        "dutch-orange": "#FF6600",
        "dutch-red": "#AE0F0F",
      },
    },
  },
  plugins: [],
};
