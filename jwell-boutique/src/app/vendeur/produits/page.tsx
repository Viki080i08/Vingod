"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Plus, Edit, Trash2, Package } from "lucide-react";
import { SellerNav } from "@/components/SellerNav";
import { Product } from "@/types";
import { parseImages, formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function VendeurProduitsPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);

  const loadProducts = () => {
    fetch("/api/products?all=true")
      .then((r) => {
        if (!r.ok) router.push("/vendeur/login");
        return r.json();
      })
      .then((data) => setProducts(data.products || []));
  };

  useEffect(() => {
    loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer ce produit ?")) return;
    await fetch(`/api/products/${id}`, { method: "DELETE" });
    loadProducts();
  };

  const toggleActive = async (product: Product) => {
    await fetch(`/api/products/${product.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isActive: !product.isActive }),
    });
    loadProducts();
  };

  return (
    <div className="min-h-screen bg-stone-100">
      <SellerNav onLogout={() => router.push("/vendeur/login")} active="produits" />

      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Mes produits</h1>
            <p className="text-stone-500">{products.length} produit(s)</p>
          </div>
          <Link href="/vendeur/produits/nouveau">
            <Button>
              <Plus className="h-4 w-4" />
              Ajouter un produit
            </Button>
          </Link>
        </div>

        <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-stone-200 bg-stone-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Produit</th>
                <th className="px-4 py-3 text-left font-medium hidden sm:table-cell">Catégorie</th>
                <th className="px-4 py-3 text-left font-medium">Prix</th>
                <th className="px-4 py-3 text-left font-medium">Stock</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">Statut</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {products.map((product) => {
                const images = parseImages(product.images);
                return (
                  <tr key={product.id} className="hover:bg-stone-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg bg-stone-100">
                          {images[0] ? (
                            <Image src={images[0]} alt="" fill className="object-cover" />
                          ) : (
                            <div className="flex h-full items-center justify-center">
                              <Package className="h-4 w-4 text-stone-300" />
                            </div>
                          )}
                        </div>
                        <div>
                          <p className="font-medium">{product.name}</p>
                          {product.brand && (
                            <p className="text-xs text-stone-400">{product.brand}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <Badge>{product.category}</Badge>
                    </td>
                    <td className="px-4 py-3 font-medium">{formatPrice(product.price)}</td>
                    <td className="px-4 py-3">
                      <Badge variant={product.stock <= 5 ? "warning" : "success"}>
                        {product.stock}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <button onClick={() => toggleActive(product)}>
                        <Badge variant={product.isActive ? "success" : "default"}>
                          {product.isActive ? "Actif" : "Inactif"}
                        </Badge>
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Link href={`/vendeur/produits/${product.id}`}>
                          <Button size="sm" variant="ghost">
                            <Edit className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Button size="sm" variant="ghost" onClick={() => handleDelete(product.id)}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {products.length === 0 && (
            <div className="py-12 text-center text-stone-400">
              Aucun produit. Ajoutez votre premier produit !
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
