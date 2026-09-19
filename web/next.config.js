/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The Google Fonts stylesheet is loaded with a plain <link> in layout.tsx so
  // it fetches in the browser at runtime. Next's build-time font optimization
  // tries to download it during the build as well, which hangs for minutes on
  // any machine that can't reach fonts.googleapis.com and then gives up
  // anyway. The page renders identically either way.
  optimizeFonts: false,
};

module.exports = nextConfig;
