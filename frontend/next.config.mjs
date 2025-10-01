/** @type {import('next').NextConfig} */
const securityHeaders = [
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin',
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Permissions-Policy',
    value: 'geolocation=(), microphone=(), camera=()'
  },
  // CSP básica (report-only placeholder: mover a enforce tras validar)
  // Nota: Ajustar 'self' y dominios externos (cdn, analytics) antes de producción
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'", // Ajustar para remover unsafe* cuando se pueda
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self' data:",
    // Allow local dev backend hosts (both localhost and 127.0.0.1) for fetch/ws in dev
    "connect-src 'self' https://localhost:8000 http://localhost:8000 http://127.0.0.1:8000 ws://localhost:8000 ws://127.0.0.1:8000",
      "frame-ancestors 'self'",
      "base-uri 'self'",
      "form-action 'self'"
    ].join('; ')
  }
];

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compiler: {
    emotion: true,
  },
  transpilePackages: ['@mui/material', '@mui/x-data-grid', '@mui/icons-material'],
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/clientes/',
        destination: 'http://127.0.0.1:8000/api/clientes/',
      },
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;