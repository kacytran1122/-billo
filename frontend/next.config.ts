import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  agentRules: false,
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
