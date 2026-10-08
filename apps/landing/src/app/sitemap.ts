import type { MetadataRoute } from "next";
import { siteUrl } from "@/content/site";
import { status } from "@/content/status";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${siteUrl}/`,
      // The page's content is dated by its status line.
      lastModified: status.isoDate,
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
