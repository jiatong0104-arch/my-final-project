// Tailwind Play CDN 的設定：網站的顏色與字體（要在 cdn.tailwindcss.com 之後載入）
tailwind.config = {
  theme: {
    extend: {
      colors: {
        paper: "#FBFBF8",
        grid: "#DCE5F2",
        ink: "#1C2638",
        soft: "#5B6475",
        student: { DEFAULT: "#2547B5", light: "#E8EDFB", dark: "#1A3487" },
        teacher: { DEFAULT: "#C2362E", light: "#FBEAE8", dark: "#952720" },
        marker: "#FFE45C",
      },
      fontFamily: {
        hand: ['"LXGW WenKai TC"', '"Kaiti TC"', "DFKai-SB", "serif"],
        sans: ['"Noto Sans TC"', '"PingFang TC"', '"Microsoft JhengHei"', "system-ui", "sans-serif"],
      },
    },
  },
};
