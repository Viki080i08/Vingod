"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ShoppingCart, Package, Minus, Plus } from "lucide-react";
import { Product } from "@/types";
import { parseImages, formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useCart } from "@/store/cart";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState(0);
  const addItem = useCart((s) => s.addItem);

  useEffect(() => {
    fetch(`/api/products/${id}`)
      .then((r) => r.json())
      .then((data) => setProduct(data.product));
  }, [id]);

  if (!product) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-20 text-center">
        <div className="mx-auto h-8 w-48 animate-pulse rounded bg-stone-200" />
      </div>
    );
  }

  const images = parseImages(product.images);
  const inStock = product.stock > 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <Link
        href="/produits"
        className="mb-6 inline-flex items-center gap-1 text-sm text-stone-500 hover:text-amber-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour aux produits
      </Link>

      <div className="grid gap-10 lg:grid-cols-2">
        <div>
          <div className="relative mb-3 aspect-square overflow-hidden rounded-xl bg-stone-100">
            {images[selectedImage] ? (
              <Image
                src={images[selectedImage]}
                alt={product.name}
                fill
                className="object-cover"
                priority
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <Package className="h-20 w-20 text-stone-300" />
              </div>
            )}
          </div>
          {images.length > 1 && (
            <div className="flex gap-2">
              {images.map((img, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedImage(i)}
                  className={`relative h-16 w-16 overflow-hidden rounded-lg border-2 ${
                    selectedImage === i ? "border-amber-600" : "border-transparent"
                  }`}
                >
                  <Image src={img} alt="" fill className="object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {product.brand && (
              <span className="text-sm font-medium uppercase text-amber-700">{product.brand}</span>
            )}
            <Badge>{product.category}</Badge>
            {!inStock && <Badge variant="danger">Rupture de stock</Badge>}
          </div>
          <h1 className="mb-4 text-3xl font-bold text-stone-900">{product.name}</h1>
          <p className="mb-6 text-3xl font-bold text-amber-700">{formatPrice(product.price)}</p>

          {product.description && (
            <p className="mb-6 text-stone-600 leading-relaxed">{product.description}</p>
          )}

          <div className="mb-6 space-y-2 rounded-lg bg-stone-100 p-4 text-sm">
            {product.nicotine && (
              <p>
                <span className="font-medium">Nicotine :</span> {product.nicotine}
              </p>
            )}
            {product.flavor && (
              <p>
                <span className="font-medium">Saveur :</span> {product.flavor}
              </p>
            )}
            <p>
              <span className="font-medium">Stock :</span>{" "}
              {inStock ? (
                <span className="text-green-700">{product.stock} disponible(s)</span>
              ) : (
                <span className="text-red-600">Indisponible</span>
              )}
            </p>
          </div>

          {inStock && (
            <div className="flex items-center gap-4">
              <div className="flex items-center rounded-lg border border-stone-300">
                <button
                  className="px-3 py-2 hover:bg-stone-100"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                >
                  <Minus className="h-4 w-4" />
                </button>
                <span className="w-10 text-center font-medium">{quantity}</span>
                <button
                  className="px-3 py-2 hover:bg-stone-100"
                  onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
              <Button
                size="lg"
                className="flex-1"
                onClick={() => {
                  addItem({
                    productId: product.id,
                    name: product.name,
                    price: product.price,
                    image: images[0] || "",
                    stock: product.stock,
                    quantity,
                  });
                }}
              >
                <ShoppingCart className="h-5 w-5" />
                Ajouter au panier
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
