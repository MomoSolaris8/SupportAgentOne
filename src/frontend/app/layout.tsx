import type { Metadata } from "next";
import "./globals.css";
import { I18nProvider } from "./components/i18n";

export const metadata: Metadata = {
  title: "SupportAgent Claims Control",
  description: "Evidence-bound insurance claims review and controlled action workspace"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body><I18nProvider>{children}</I18nProvider></body>
    </html>
  );
}
