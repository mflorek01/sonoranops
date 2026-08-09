/** @type {import('next').NextConfig} */
const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const basePath = rawBasePath === "/" ? "" : `/${rawBasePath.replace(/^\/+|\/+$/g, "")}`.replace(/^\/$/, "");
const nextConfig = { reactStrictMode: true, basePath };

export default nextConfig;
