"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { SellerNav } from "@/components/SellerNav";
import { Package, ShoppingBag, TrendingUp, AlertTriangle, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { formatPrice, ORDER_STATUSES } from "@/lib/utils";
import { Order } from "@/types";

interface Stats {
  totalProducts: number;
  activeProducts: number;
  lowStockProducts: number;
  totalOrders: number;
  paidOrders: number;
  revenue: number;
  recentOrders: Order[];
  lowStock: { id: string; name: string; stock: number }[];
}

export default function VendeurDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [sellerName, setSellerName] = useState("");

  useEffect(() => {
    Promise.all([fetch("/api/auth/me"), fetch("/api/stats")])
      .then(async ([meRes, statsRes]) => {
        if (!meRes.ok) {
          router.push("/vendeur/login");
          return;
        }
        const me = await meRes.json();
        setSellerName(me.seller.name);
        const data = await statsRes.json();
        setStats(data.stats);
      });
  }, [router]);

  if (!stats) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-48 animate-pulse rounded bg-stone-200" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-100">
      <SellerNav active="dashboard" onLogout={() => router.push("/vendeur/login")} />

      <div className="mx-auto max-w-7xl px-4 py-4">
        <p className="text-sm text-stone-500">Bienvenue, {sellerName}</p>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex justify-end">
          <Link href="/vendeur/produits/nouveau">
            <Button size="sm">
              <Plus className="h-4 w-4" />
              Nouveau produit
            </Button>
          </Link>
        </div>
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Produits actifs", value: stats.activeProducts, icon: Package, color: "text-blue-600" },
            { label: "Commandes payées", value: stats.paidOrders, icon: ShoppingBag, color: "text-green-600" },
            { label: "Chiffre d'affaires", value: formatPrice(stats.revenue), icon: TrendingUp, color: "text-amber-600" },
            { label: "Stock faible", value: stats.lowStockProducts, icon: AlertTriangle, color: "text-red-600" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-xl border border-stone-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-stone-500">{label}</p>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <p className="mt-1 text-2xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-stone-200 bg-white p-5">
            <h2 className="mb-4 font-semibold">Commandes récentes</h2>
            {stats.recentOrders.length > 0 ? (
              <div className="space-y-3">
                {stats.recentOrders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between rounded-lg bg-stone-50 p-3">
                    <div>
                      <p className="text-sm font-medium">{order.customerName}</p>
                      <p className="text-xs text-stone-500">
                        {new Date(order.createdAt).toLocaleDateString("fr-FR")}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">{formatPrice(order.totalAmount)}</p>
                      <Badge className={ORDER_STATUSES[order.status as keyof typeof ORDER_STATUSES]?.color}>
                        {ORDER_STATUSES[order.status as keyof typeof ORDER_STATUSES]?.label || order.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">Aucune commande pour le moment</p>
            )}
            <Link href="/vendeur/ventes" className="mt-3 block text-sm text-amber-700 hover:underline">
              Voir toutes les ventes →
            </Link>
          </div>

          <div className="rounded-xl border border-stone-200 bg-white p-5">
            <h2 className="mb-4 font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              Alertes stock faible
            </h2>
            {stats.lowStock.length > 0 ? (
              <div className="space-y-2">
                {stats.lowStock.map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-lg bg-amber-50 p-3">
                    <span className="text-sm">{p.name}</span>
                    <Badge variant="warning">{p.stock} restant(s)</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">Tous les stocks sont OK</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
