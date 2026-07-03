"use client";

import Link from "next/link";
import Image from "next/image";
import { ShoppingCart, Package } from "lucide-react";
import { Product } from "@/types";
import { parseImages, formatPrice } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useCart } from "@/store/cart";

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const images = parseImages(product.images);
  const addItem = useCart((s) => s.addItem);
  const inStock = product.stock > 0;

  return (
    <div className="group flex flex-col overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <Link href={`/produits/${product.id}`} className="relative aspect-square overflow-hidden bg-stone-100">
        {images[0] ? (
          <Image
            src={images[0]}
            alt={product.name}
            fill
            className="object-cover transition-transform group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, 25vw"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Package className="h-12 w-12 text-stone-300" />
          </div>
        )}
        {product.stock <= 5 && product.stock > 0 && (
          <div className="absolute left-2 top-2">
            <Badge variant="warning">Plus que {product.stock}</Badge>
          </div>
        )}
        {!inStock && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <Badge variant="danger">Rupture de stock</Badge>
          </div>
        )}
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <div className="mb-1 flex items-center gap-2">
          {product.brand && (
            <span className="text-xs font-medium uppercase tracking-wide text-amber-700">
              {product.brand}
            </span>
          )}
          <Badge>{product.category}</Badge>
        </div>
        <Link href={`/produits/${product.id}`}>
          <h3 className="mb-1 font-semibold text-stone-900 line-clamp-2 hover:text-amber-700">
            {product.name}
          </h3>
        </Link>
        {product.flavor && (
          <p className="mb-2 text-xs text-stone-500">Saveur : {product.flavor}</p>
        )}
        <div className="mt-auto flex items-center justify-between pt-2">
          <div>
            <p className="text-lg font-bold text-stone-900">{formatPrice(product.price)}</p>
            <p className="text-xs text-stone-500">
              {inStock ? `${product.stock} en stock` : "Indisponible"}
            </p>
          </div>
          <Button
            size="sm"
            disabled={!inStock}
            onClick={() =>
              addItem({
                productId: product.id,
                name: product.name,
                price: product.price,
                image: images[0] || "",
                stock: product.stock,
              })
            }
          >
            <ShoppingCart className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
