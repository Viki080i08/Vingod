import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(price);
}

export function parseImages(images: string): string[] {
  try {
    const parsed = JSON.parse(images);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const ORDER_STATUSES = {
  PENDING: { label: "En attente", color: "bg-yellow-100 text-yellow-800" },
  PAID: { label: "Payée", color: "bg-green-100 text-green-800" },
  PREPARING: { label: "En préparation", color: "bg-blue-100 text-blue-800" },
  READY: { label: "Prête", color: "bg-purple-100 text-purple-800" },
  COMPLETED: { label: "Terminée", color: "bg-gray-100 text-gray-800" },
  CANCELLED: { label: "Annulée", color: "bg-red-100 text-red-800" },
} as const;

export type OrderStatus = keyof typeof ORDER_STATUSES;

export const CATEGORIES = [
  "E-liquides",
  "Puffs",
  "Pods",
  "Mods",
  "Résistances",
  "Accessoires",
  "CBD",
  "Autre",
] as const;
