import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    // Dependencies and packages/brand resolve through the workspace root.
    root: path.join(__dirname, "../.."),
    rules: {
      // Tailwind compiles the global stylesheets. Component styles are CSS
      // Modules and must stay with Turbopack's own handling, or their class
      // names are emitted unscoped and `styles.x` is undefined.
      "*.css": {
        condition: { not: { path: /\.module\.css$/ } },
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
