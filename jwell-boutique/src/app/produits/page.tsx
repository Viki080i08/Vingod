"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { ProductCard } from "@/components/ProductCard";
import { Input, Select } from "@/components/ui/Input";
import { Product } from "@/types";
import { CATEGORIES } from "@/lib/utils";

export default function ProduitsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category !== "all") params.set("category", category);

    setLoading(true);
    fetch(`/api/products?${params}`)
      .then((r) => r.json())
      .then((data) => setProducts(data.products || []))
      .finally(() => setLoading(false));
  }, [search, category]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-stone-900">Nos produits</h1>
        <p className="text-stone-500">Parcourez notre catalogue complet</p>
      </div>

      <div className="mb-8 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
          <Input
            placeholder="Rechercher un produit, une marque..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="sm:w-48"
        >
          <option value="all">Toutes catégories</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </Select>
      </div>

      {loading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-80 animate-pulse rounded-xl bg-stone-200" />
          ))}
        </div>
      ) : products.length > 0 ? (
        <>
          <p className="mb-4 text-sm text-stone-500">{products.length} produit(s)</p>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-stone-300 py-16 text-center">
          <p className="text-stone-500">Aucun produit trouvé</p>
        </div>
      )}
    </div>
  );
}
