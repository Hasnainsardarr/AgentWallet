export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DeFi Dark Theme Colors - Enhanced
        'defi-bg': '#1a1625',          // Deep purple-charcoal background
        'defi-bg-light': '#251d35',    // Lighter purple for cards
        'defi-bg-lighter': '#2d2440',  // Even lighter for hover states
        'defi-bg-accent': '#1f1a2e',   // Accent background for gradients
        'defi-purple': '#6b4ce6',      // Bright blue-purple for primary buttons
        'defi-purple-dark': '#5a3dc5', // Darker purple for hover
        'defi-purple-light': '#8b6ef9', // Lighter purple for accents
        'defi-lavender': '#b4a0ff',    // Lavender for outlines and secondary
        'defi-lavender-light': '#d4c9ff', // Light lavender for text
        'defi-text': '#e8e5f0',        // Light lavender text
        'defi-text-dim': '#9e94b8',    // Dimmed text
        'defi-border': '#3d3453',      // Border color
        'defi-success': '#10b981',     // Success green
        'defi-warning': '#f59e0b',     // Warning amber
        'defi-error': '#ef4444',       // Error red
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'gradient-shimmer': 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(107, 76, 230, 0.2), 0 0 10px rgba(107, 76, 230, 0.1)' },
          '100%': { boxShadow: '0 0 10px rgba(107, 76, 230, 0.4), 0 0 20px rgba(107, 76, 230, 0.2)' },
        },
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(107, 76, 230, 0.3)',
        'glow-md': '0 0 20px rgba(107, 76, 230, 0.4)',
        'glow-lg': '0 0 30px rgba(107, 76, 230, 0.5)',
        'inner-glow': 'inset 0 0 20px rgba(107, 76, 230, 0.2)',
      },
    },
  },
  plugins: [],
}

