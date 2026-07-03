"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Order } from "@/types";
import { formatPrice, ORDER_STATUSES } from "@/lib/utils";
import { Select } from "@/components/ui/Input";
import { SellerNav } from "@/components/SellerNav";

export default function VendeurVentesPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);

  const loadOrders = () => {
    fetch("/api/orders")
      .then((r) => {
        if (!r.ok) router.push("/vendeur/login");
        return r.json();
      })
      .then((data) => setOrders(data.orders || []));
  };

  useEffect(() => {
    loadOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const updateStatus = async (orderId: string, status: string) => {
    await fetch("/api/orders", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orderId, status }),
    });
    loadOrders();
  };

  return (
    <div className="min-h-screen bg-stone-100">
      <SellerNav active="ventes" onLogout={() => router.push("/vendeur/login")} />

      <div className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Ventes & commandes</h1>

        <div className="space-y-4">
          {orders.map((order) => (
            <div key={order.id} className="rounded-xl border border-stone-200 bg-white p-5">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{order.customerName}</p>
                  <p className="text-sm text-stone-500">{order.customerEmail}</p>
                  {order.customerPhone && (
                    <p className="text-sm text-stone-500">{order.customerPhone}</p>
                  )}
                  <p className="mt-1 text-xs text-stone-400">
                    {new Date(order.createdAt).toLocaleString("fr-FR")} — Ref: {order.id.slice(-8)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-amber-700">
                    {formatPrice(order.totalAmount)}
                  </p>
                  <Select
                    value={order.status}
                    onChange={(e) => updateStatus(order.id, e.target.value)}
                    className="mt-2 w-44 text-sm"
                  >
                    {Object.entries(ORDER_STATUSES).map(([key, { label }]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="rounded-lg bg-stone-50 p-3">
                <p className="mb-2 text-xs font-medium uppercase text-stone-400">Articles</p>
                {order.items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm py-1">
                    <span>
                      {item.product?.name || "Produit"} × {item.quantity}
                    </span>
                    <span className="font-medium">{formatPrice(item.price * item.quantity)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {orders.length === 0 && (
            <div className="rounded-xl border border-dashed border-stone-300 py-16 text-center text-stone-400">
              Aucune commande pour le moment
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
