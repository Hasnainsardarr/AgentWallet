export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DeFi Dark Theme Colors
        'defi-bg': '#1a1625',          // Deep purple-charcoal background
        'defi-bg-light': '#251d35',    // Lighter purple for cards
        'defi-bg-lighter': '#2d2440',  // Even lighter for hover states
        'defi-purple': '#6b4ce6',      // Bright blue-purple for primary buttons
        'defi-purple-dark': '#5a3dc5', // Darker purple for hover
        'defi-lavender': '#b4a0ff',    // Lavender for outlines and secondary
        'defi-lavender-light': '#d4c9ff', // Light lavender for text
        'defi-text': '#e8e5f0',        // Light lavender text
        'defi-text-dim': '#9e94b8',    // Dimmed text
        'defi-border': '#3d3453',      // Border color
      }
    },
  },
  plugins: [],
}

