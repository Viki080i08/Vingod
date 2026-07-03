"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShoppingCart, MapPin, Phone, Menu, X } from "lucide-react";
import { useState } from "react";
import { SHOP } from "@/lib/constants";
import { useCart } from "@/store/cart";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Accueil" },
  { href: "/produits", label: "Produits" },
  { href: "/#contact", label: "Contact" },
];

export function Header() {
  const pathname = usePathname();
  const itemCount = useCart((s) => s.itemCount());
  const [mobileOpen, setMobileOpen] = useState(false);

  const isSeller = pathname.startsWith("/vendeur");

  if (isSeller) return null;

  return (
    <header className="sticky top-0 z-50 border-b border-stone-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-stone-900 text-sm font-bold text-white">
            JW
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-bold text-stone-900 leading-tight">THE VAPE SHOP</p>
            <p className="text-xs text-amber-700">by Jwell FDJ — since 2013</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "text-sm font-medium transition-colors hover:text-amber-700",
                pathname === link.href ? "text-amber-700" : "text-stone-600"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <a
            href={SHOP.phoneHref}
            className="hidden items-center gap-1 text-sm text-stone-600 hover:text-amber-700 lg:flex"
          >
            <Phone className="h-4 w-4" />
            {SHOP.phone}
          </a>
          <Link
            href="/panier"
            className="relative flex items-center gap-1 rounded-lg bg-stone-100 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-200"
          >
            <ShoppingCart className="h-4 w-4" />
            <span className="hidden sm:inline">Panier</span>
            {itemCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-amber-600 text-xs text-white">
                {itemCount}
              </span>
            )}
          </Link>
          <button
            className="md:hidden rounded-lg p-2 hover:bg-stone-100"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="border-t border-stone-200 px-4 py-3 md:hidden">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block py-2 text-sm font-medium text-stone-600"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </Link>
          ))}
          <a href={SHOP.mapsUrl} className="flex items-center gap-2 py-2 text-sm text-amber-700">
            <MapPin className="h-4 w-4" />
            Itinéraire
          </a>
        </nav>
      )}
    </header>
  );
}
