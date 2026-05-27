/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  rewrites() {
    return [
      {
        source: "/metrics",
        destination: "/api/metrics",
      },
    ];
  },
};

export default nextConfig;
