import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import path from "path";
import { SHOP } from "./constants";

export interface GoogleReview {
  author: string;
  rating: number;
  text: string;
  date: string;
  profilePhoto?: string;
}

export interface GoogleReviewsData {
  rating: number;
  reviewCount: number;
  reviews: GoogleReview[];
  googleMapsUrl: string;
  syncedAt: string;
}

const CACHE_FILE = path.join(process.cwd(), "data", "google-reviews-cache.json");
let memoryCache: { data: GoogleReviewsData; expires: number } | null = null;

function readFileCache(): GoogleReviewsData | null {
  try {
    if (!existsSync(CACHE_FILE)) return null;
    const raw = readFileSync(CACHE_FILE, "utf-8");
    const data = JSON.parse(raw) as GoogleReviewsData;
    if (data.reviewCount > 0) return data;
    return null;
  } catch {
    return null;
  }
}

function writeFileCache(data: GoogleReviewsData) {
  mkdirSync(path.dirname(CACHE_FILE), { recursive: true });
  writeFileSync(CACHE_FILE, JSON.stringify(data, null, 2), "utf-8");
}

async function findPlaceId(apiKey: string): Promise<string | null> {
  const res = await fetch("https://places.googleapis.com/v1/places:searchText", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
    },
    body: JSON.stringify({
      textQuery: SHOP.googleSearchQuery,
      languageCode: "fr",
      regionCode: "FR",
    }),
  });

  if (!res.ok) return null;

  const data = await res.json();
  const place = data.places?.[0];
  const id = place?.id as string | undefined;
  return id?.startsWith("places/") ? id.replace("places/", "") : id || null;
}

async function fetchFromGoogle(apiKey: string, placeId?: string): Promise<GoogleReviewsData | null> {
  const id = placeId || (await findPlaceId(apiKey));
  if (!id) return null;

  const res = await fetch(`https://places.googleapis.com/v1/places/${id}`, {
    headers: {
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask":
        "id,displayName,rating,userRatingCount,googleMapsUri,reviews.authorAttribution.displayName,reviews.authorAttribution.photoUri,reviews.rating,reviews.text,reviews.relativePublishTimeDescription",
    },
  });

  if (!res.ok) return null;

  const place = await res.json();

  const reviews: GoogleReview[] = (place.reviews || []).map(
    (r: {
      authorAttribution?: { displayName?: string; photoUri?: string };
      rating?: number;
      text?: { text?: string };
      relativePublishTimeDescription?: string;
    }) => ({
      author: r.authorAttribution?.displayName || "Client Google",
      rating: r.rating || 5,
      text: r.text?.text || "",
      date: r.relativePublishTimeDescription || "",
      profilePhoto: r.authorAttribution?.photoUri,
    })
  );

  return {
    rating: place.rating || 0,
    reviewCount: place.userRatingCount || 0,
    reviews,
    googleMapsUrl: place.googleMapsUri || SHOP.mapsReviewsUrl,
    syncedAt: new Date().toISOString(),
  };
}

const emptyData = (): GoogleReviewsData => ({
  rating: 0,
  reviewCount: 0,
  reviews: [],
  googleMapsUrl: SHOP.mapsReviewsUrl,
  syncedAt: "",
});

export async function getGoogleReviews(): Promise<GoogleReviewsData> {
  if (memoryCache && memoryCache.expires > Date.now()) {
    return memoryCache.data;
  }

  const fileCache = readFileCache();
  if (fileCache) {
    memoryCache = { data: fileCache, expires: Date.now() + 60 * 60 * 1000 };
    return fileCache;
  }

  const apiKey = process.env.GOOGLE_PLACES_API_KEY;
  if (!apiKey) return emptyData();

  try {
    const data = await fetchFromGoogle(apiKey, process.env.GOOGLE_PLACE_ID || undefined);
    if (!data || data.reviewCount === 0) return emptyData();

    writeFileCache(data);
    memoryCache = { data, expires: Date.now() + 6 * 60 * 60 * 1000 };
    return data;
  } catch {
    return emptyData();
  }
}

export async function syncGoogleReviews(): Promise<GoogleReviewsData> {
  const apiKey = process.env.GOOGLE_PLACES_API_KEY;
  if (!apiKey) {
    throw new Error("GOOGLE_PLACES_API_KEY manquant dans .env");
  }

  const data = await fetchFromGoogle(apiKey, process.env.GOOGLE_PLACE_ID || undefined);
  if (!data) {
    throw new Error("Impossible de récupérer les avis Google");
  }

  writeFileCache(data);
  memoryCache = { data, expires: Date.now() + 6 * 60 * 60 * 1000 };
  return data;
}
