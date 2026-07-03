"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MapPin, Phone, Clock, Star } from "lucide-react";
import { SHOP } from "@/lib/constants";
import type { GoogleReviewsData } from "@/lib/google-reviews";

export function Footer() {
  const pathname = usePathname();
  const [reviews, setReviews] = useState<GoogleReviewsData | null>(null);

  useEffect(() => {
    fetch("/api/reviews")
      .then((r) => r.json())
      .then(setReviews)
      .catch(() => null);
  }, []);

  if (pathname.startsWith("/vendeur")) return null;

  return (
    <footer id="contact" className="bg-stone-900 text-stone-300">
      <div className="mx-auto max-w-7xl px-4 py-12">
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <h3 className="mb-3 text-lg font-bold text-white">{SHOP.name}</h3>
            <p className="mb-4 text-sm text-stone-400">{SHOP.tagline}</p>
            {reviews && reviews.reviewCount > 0 && (
              <div className="flex items-center gap-1 text-amber-400">
                <Star className="h-4 w-4 fill-current" />
                <span className="text-sm font-medium">{reviews.rating}/5</span>
                <span className="text-sm text-stone-500">
                  ({reviews.reviewCount} avis Google)
                </span>
              </div>
            )}
          </div>

          <div>
            <h4 className="mb-3 font-semibold text-white">Contact</h4>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                <span>
                  {SHOP.address}
                  <br />
                  {SHOP.city}, {SHOP.country}
                </span>
              </li>
              <li className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-amber-500" />
                <a href={SHOP.phoneHref} className="hover:text-white">
                  {SHOP.phone}
                </a>
              </li>
              <li className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-500" />
                {SHOP.hours}
              </li>
            </ul>
          </div>

          <div>
            <h4 className="mb-3 font-semibold text-white">Liens utiles</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/produits" className="hover:text-white">
                  Nos produits
                </Link>
              </li>
              <li>
                <a
                  href={SHOP.mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white"
                >
                  Obtenir l&apos;itinéraire
                </a>
              </li>
              <li>
                <a
                  href={SHOP.mapsReviewsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white"
                >
                  Nos avis Google
                </a>
              </li>
              <li>
                <Link href="/vendeur/login" className="hover:text-white">
                  Espace vendeur
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-stone-800 pt-6 text-center text-xs text-stone-500">
          © {new Date().getFullYear()} {SHOP.name}. Vente réservée aux majeurs (+18 ans).
        </div>
      </div>
    </footer>
  );
}
