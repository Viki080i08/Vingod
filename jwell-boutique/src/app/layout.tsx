import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "The Vape Shop by Jwell FDJ — Boutique e-cigarette Ménétrol",
  description:
    "Boutique de cigarettes électroniques à Ménétrol depuis 2013. E-liquides, puffs, pods et accessoires. Commandez en ligne ou venez nous voir !",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={`${inter.className} min-h-screen bg-stone-50 text-stone-900 antialiased`}>
        <Header />
        <main className="min-h-[calc(100vh-200px)]">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
