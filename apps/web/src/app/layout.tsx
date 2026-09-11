import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "GridSentinel | Operasyon Merkezi",
  description:
    "Şirket içi pano ve hücre izleme, açıklanabilir risk ve sentetik demo ortamı.",
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
