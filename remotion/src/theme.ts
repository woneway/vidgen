export const COLORS = {
  bgDark: "#0d1117",
  bgCard: "#161b22",
  bgCardLight: "#1c2128",
  border: "#30363d",
  textPrimary: "#e6edf3",
  textSecondary: "#8b949e",
  textMuted: "#6e7681",
  accentBlue: "#388af4",
  accentGreen: "#3fb950",
  accentOrange: "#d29922",
  accentPurple: "#a371f7",
  accentPink: "#f778ba",
  accentRed: "#f85149",
} as const;

export const FONTS = {
  // System fonts available in headless Chrome on macOS
  sans: "'PingFang SC', 'Hiragino Sans GB', 'STHeiti', 'Noto Sans SC', 'Microsoft YaHei', sans-serif",
  mono: "'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace",
} as const;

export const SIZES = {
  width: 1080,
  height: 1920,
  fps: 25,
  transitionDuration: 20, // frames for scene transitions
  subtitleFontSize: 42,
  titleFontSize: 72,
  headingFontSize: 56,
  bodyFontSize: 36,
  smallFontSize: 28,
  codeFontSize: 22,
  padding: 60,
} as const;
