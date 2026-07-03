"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Trash2, Minus, Plus, ShoppingBag, Package } from "lucide-react";
import { useCart } from "@/store/cart";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function PanierPage() {
  const { items, removeItem, updateQuantity, total } = useCart();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [customer, setCustomer] = useState({ name: "", email: "", phone: "" });
  const [ageConfirmed, setAgeConfirmed] = useState(false);

  const handleCheckout = async () => {
    if (!customer.name || !customer.email) {
      setError("Veuillez remplir votre nom et email");
      return;
    }
    if (!ageConfirmed) {
      setError("Vous devez confirmer être majeur (+18 ans)");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: items.map((i) => ({ productId: i.productId, quantity: i.quantity })),
          customerName: customer.name,
          customerEmail: customer.email,
          customerPhone: customer.phone,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur paiement");

      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du paiement");
    } finally {
      setLoading(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <ShoppingBag className="mx-auto mb-4 h-16 w-16 text-stone-300" />
        <h1 className="mb-2 text-2xl font-bold">Votre panier est vide</h1>
        <p className="mb-6 text-stone-500">Découvrez nos produits et ajoutez-les à votre panier</p>
        <Link href="/produits">
          <Button>Voir les produits</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-8 text-3xl font-bold">Mon panier</h1>

      <div className="grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-3 space-y-4">
          {items.map((item) => (
            <div
              key={item.productId}
              className="flex gap-4 rounded-xl border border-stone-200 bg-white p-4"
            >
              <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-stone-100">
                {item.image ? (
                  <Image src={item.image} alt={item.name} fill className="object-cover" />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Package className="h-8 w-8 text-stone-300" />
                  </div>
                )}
              </div>
              <div className="flex flex-1 flex-col">
                <h3 className="font-medium">{item.name}</h3>
                <p className="text-sm text-amber-700">{formatPrice(item.price)}</p>
                <div className="mt-auto flex items-center justify-between">
                  <div className="flex items-center rounded border border-stone-200">
                    <button
                      className="px-2 py-1 hover:bg-stone-50"
                      onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                    >
                      <Minus className="h-3 w-3" />
                    </button>
                    <span className="w-8 text-center text-sm">{item.quantity}</span>
                    <button
                      className="px-2 py-1 hover:bg-stone-50"
                      onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                    >
                      <Plus className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">
                      {formatPrice(item.price * item.quantity)}
                    </span>
                    <button
                      onClick={() => removeItem(item.productId)}
                      className="text-stone-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-24 rounded-xl border border-stone-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold">Récapitulatif</h2>
            <div className="mb-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-stone-500">Sous-total</span>
                <span>{formatPrice(total())}</span>
              </div>
              <div className="flex justify-between border-t border-stone-200 pt-2 text-base font-bold">
                <span>Total</span>
                <span className="text-amber-700">{formatPrice(total())}</span>
              </div>
            </div>

            <div className="mb-4 space-y-3">
              <Input
                placeholder="Nom complet *"
                value={customer.name}
                onChange={(e) => setCustomer({ ...customer, name: e.target.value })}
              />
              <Input
                type="email"
                placeholder="Email *"
                value={customer.email}
                onChange={(e) => setCustomer({ ...customer, email: e.target.value })}
              />
              <Input
                type="tel"
                placeholder="Téléphone (optionnel)"
                value={customer.phone}
                onChange={(e) => setCustomer({ ...customer, phone: e.target.value })}
              />
            </div>

            <label className="mb-4 flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={ageConfirmed}
                onChange={(e) => setAgeConfirmed(e.target.checked)}
                className="mt-0.5"
              />
              <span>Je certifie être majeur(e) et avoir plus de 18 ans</span>
            </label>

            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

            <Button className="w-full" size="lg" disabled={loading} onClick={handleCheckout}>
              {loading ? "Redirection..." : "Payer avec Stripe"}
            </Button>
            <p className="mt-2 text-center text-xs text-stone-400">
              Paiement sécurisé par Stripe
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
