"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Image from "next/image";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input, Textarea, Select } from "@/components/ui/Input";
import { CATEGORIES, parseImages } from "@/lib/utils";
import { Product } from "@/types";
import { SellerNav } from "@/components/SellerNav";

export default function EditProduitPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    brand: "",
    category: "Autre",
    price: "",
    stock: "",
    nicotine: "",
    flavor: "",
    isActive: true,
    images: [] as string[],
  });

  useEffect(() => {
    fetch(`/api/products/${id}`)
      .then((r) => {
        if (!r.ok) router.push("/vendeur/login");
        return r.json();
      })
      .then((data: { product: Product }) => {
        const p = data.product;
        setForm({
          name: p.name,
          description: p.description || "",
          brand: p.brand || "",
          category: p.category,
          price: String(p.price),
          stock: String(p.stock),
          nicotine: p.nicotine || "",
          flavor: p.flavor || "",
          isActive: p.isActive,
          images: parseImages(p.images),
        });
      })
      .finally(() => setLoading(false));
  }, [id, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    await fetch(`/api/products/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        price: parseFloat(form.price),
        stock: parseInt(form.stock, 10),
      }),
    });

    router.push("/vendeur/produits");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-100">
      <SellerNav active="produits" onLogout={() => router.push("/vendeur/login")} />

      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Modifier le produit</h1>

        {form.images.length > 0 && (
          <div className="mb-4 flex gap-2">
            {form.images.map((img, i) => (
              <div key={i} className="relative h-20 w-20 overflow-hidden rounded-lg">
                <Image src={img} alt="" fill className="object-cover" />
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className="rounded-xl border border-stone-200 bg-white p-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Nom *</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Description</label>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Marque</label>
              <Input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Catégorie</label>
              <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Prix (€) *</label>
              <Input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Stock *</label>
              <Input type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} required />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Nicotine</label>
              <Input value={form.nicotine} onChange={(e) => setForm({ ...form, nicotine: e.target.value })} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Saveur</label>
              <Input value={form.flavor} onChange={(e) => setForm({ ...form, flavor: e.target.value })} />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.isActive}
              onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
            />
            Produit visible sur la boutique
          </label>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => router.back()}>Annuler</Button>
            <Button type="submit" disabled={saving} className="flex-1">
              {saving ? "Enregistrement..." : "Sauvegarder"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
