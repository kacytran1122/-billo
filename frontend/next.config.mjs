const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  agentRules: false,
  turbopack: {
    root: import.meta.dirname,
  },
};

export default nextConfig;
