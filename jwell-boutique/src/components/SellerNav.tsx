"use client";

import Link from "next/link";
import { BarChart3, Package, ShoppingBag, LogOut } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface SellerNavProps {
  active: "dashboard" | "produits" | "ventes";
  onLogout: () => void;
}

export function SellerNav({ active, onLogout }: SellerNavProps) {
  const links = [
    { key: "dashboard" as const, href: "/vendeur/dashboard", label: "Tableau de bord", icon: BarChart3 },
    { key: "produits" as const, href: "/vendeur/produits", label: "Produits", icon: Package },
    { key: "ventes" as const, href: "/vendeur/ventes", label: "Ventes", icon: ShoppingBag },
  ];

  return (
    <>
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <h1 className="text-xl font-bold">Espace vendeur</h1>
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              await fetch("/api/auth/logout", { method: "POST" });
              onLogout();
            }}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>
      <nav className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-7xl gap-1 px-4">
          {links.map(({ key, href, label, icon: Icon }) => (
            <Link
              key={key}
              href={href}
              className={`flex items-center gap-1 px-4 py-3 text-sm font-medium border-b-2 ${
                active === key
                  ? "border-amber-600 text-amber-700"
                  : "border-transparent text-stone-500 hover:text-stone-700"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
