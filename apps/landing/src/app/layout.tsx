import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TrackClicks } from "@/components/ui/TrackClicks";
import { metadataCopy, nav, repoUrl, siteName, siteUrl } from "@/content/site";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: metadataCopy.title,
  description: metadataCopy.description,
  applicationName: siteName,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName,
    title: metadataCopy.title,
    description: metadataCopy.description,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: metadataCopy.title,
    description: metadataCopy.description,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#12281c",
};

// No ratings and no prices: neither exists (docs/prd/landing.md, section 14).
const structuredData = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: siteName,
  description: metadataCopy.description,
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Linux",
  license: "https://opensource.org/license/mit",
  codeRepository: repoUrl,
  url: siteUrl,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <a className="skip-link" href="#main-content">
          {nav.skip}
        </a>
        {children}
        <TrackClicks />
        <script
          type="application/ld+json"
          // Static, built from constants in content/site.ts.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData).replace(/</g, "\\u003c") }}
        />
      </body>
    </html>
  );
}
