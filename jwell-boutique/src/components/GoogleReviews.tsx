"use client";

import { useEffect, useState } from "react";
import { Star, ExternalLink } from "lucide-react";
import { SHOP } from "@/lib/constants";
import type { GoogleReviewsData } from "@/lib/google-reviews";

function StarRating({ rating, size = "sm" }: { rating: number; size?: "sm" | "lg" }) {
  const cls = size === "lg" ? "h-5 w-5" : "h-4 w-4";
  return (
    <div className="flex items-center gap-0.5 text-amber-400">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={`${cls} ${i <= Math.round(rating) ? "fill-current" : "opacity-30"}`}
        />
      ))}
    </div>
  );
}

interface GoogleReviewsProps {
  variant?: "hero" | "section";
}

export function GoogleReviews({ variant = "section" }: GoogleReviewsProps) {
  const [data, setData] = useState<GoogleReviewsData | null>(null);

  useEffect(() => {
    fetch("/api/reviews")
      .then((r) => r.json())
      .then(setData)
      .catch(() => null);
  }, []);

  if (!data || data.reviewCount === 0) {
    if (variant === "hero") return null;
    return (
      <section className="bg-stone-100 py-16">
        <div className="mx-auto max-w-7xl px-4 text-center">
          <h2 className="mb-4 text-2xl font-bold text-stone-900">Avis clients</h2>
          <p className="mb-6 text-stone-500">
            Découvrez les avis de nos clients sur Google
          </p>
          <a
            href={SHOP.mapsReviewsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-white hover:bg-amber-700"
          >
            <Star className="h-4 w-4 fill-current" />
            Voir nos avis Google
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </section>
    );
  }

  if (variant === "hero") {
    return (
      <div className="flex items-center gap-1 text-amber-400">
        <StarRating rating={data.rating} />
        <span className="ml-1 text-sm text-stone-300">
          {data.rating}/5 ({data.reviewCount} avis Google)
        </span>
      </div>
    );
  }

  return (
    <section className="bg-stone-100 py-16">
      <div className="mx-auto max-w-7xl px-4">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-stone-900">Avis Google</h2>
            <div className="mt-2 flex items-center gap-3">
              <StarRating rating={data.rating} size="lg" />
              <span className="text-lg font-semibold text-stone-900">{data.rating}/5</span>
              <span className="text-stone-500">({data.reviewCount} avis)</span>
            </div>
          </div>
          <a
            href={data.googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-amber-700 hover:underline"
          >
            Tous les avis sur Google
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        {data.reviews.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.reviews.map((review, i) => (
              <div key={i} className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {review.profilePhoto ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={review.profilePhoto}
                        alt=""
                        className="h-8 w-8 rounded-full"
                      />
                    ) : (
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-700">
                        {review.author.charAt(0)}
                      </div>
                    )}
                    <span className="font-medium text-stone-900">{review.author}</span>
                  </div>
                  <StarRating rating={review.rating} />
                </div>
                {review.text && (
                  <p className="text-sm text-stone-600 leading-relaxed line-clamp-4">
                    {review.text}
                  </p>
                )}
                {review.date && (
                  <p className="mt-2 text-xs text-stone-400">{review.date}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
            <p className="mb-4 text-stone-500">
              {data.reviewCount} avis sur Google — note moyenne {data.rating}/5
            </p>
            <a
              href={data.googleMapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-amber-700 hover:underline"
            >
              Lire tous les avis sur Google Maps
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
