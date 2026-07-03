import Link from "next/link";
import { MapPin, Phone, ShoppingBag, Shield, Truck } from "lucide-react";
import { SHOP } from "@/lib/constants";
import { Button } from "@/components/ui/Button";
import { ProductCard } from "@/components/ProductCard";
import { GoogleReviews } from "@/components/GoogleReviews";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const products = await prisma.product.findMany({
    where: { isActive: true },
    orderBy: { createdAt: "desc" },
    take: 8,
  });

  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-stone-900 text-white">
        <div className="absolute inset-0 bg-[url('/hero-pattern.svg')] opacity-5" />
        <div className="relative mx-auto max-w-7xl px-4 py-20 md:py-28">
          <div className="max-w-2xl">
            <p className="mb-2 text-sm font-medium uppercase tracking-widest text-amber-400">
              Depuis 2013
            </p>
            <h1 className="mb-4 text-4xl font-bold leading-tight md:text-5xl">
              THE VAPE SHOP
              <br />
              <span className="text-amber-400">by Jwell FDJ</span>
            </h1>
            <p className="mb-6 text-lg text-stone-300">
              Votre boutique de cigarettes électroniques à Ménétrol. E-liquides, puffs, pods,
              résistances et accessoires — en magasin ou en ligne.
            </p>
            <div className="mb-8 flex flex-wrap items-center gap-4">
              <GoogleReviews variant="hero" />
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/produits">
                <Button size="lg">
                  <ShoppingBag className="h-5 w-5" />
                  Voir les produits
                </Button>
              </Link>
              <a href={SHOP.mapsUrl} target="_blank" rel="noopener noreferrer">
                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10">
                  <MapPin className="h-5 w-5" />
                  Itinéraire
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-b border-stone-200 bg-white py-10">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 sm:grid-cols-3">
          {[
            { icon: Truck, title: "Click & Collect", desc: "Commandez en ligne, récupérez en magasin" },
            { icon: Shield, title: "Produits authentiques", desc: "Marques reconnues, qualité garantie" },
            { icon: Phone, title: "Conseil expert", desc: "Une équipe passionnée à votre écoute" },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100">
                <Icon className="h-5 w-5 text-amber-700" />
              </div>
              <div>
                <h3 className="font-semibold text-stone-900">{title}</h3>
                <p className="text-sm text-stone-500">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Products */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4">
          <div className="mb-8 flex items-end justify-between">
            <div>
              <h2 className="text-2xl font-bold text-stone-900">Nos produits</h2>
              <p className="text-stone-500">Découvrez notre sélection</p>
            </div>
            <Link href="/produits" className="text-sm font-medium text-amber-700 hover:underline">
              Voir tout →
            </Link>
          </div>
          {products.length > 0 ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((product) => (
                <ProductCard key={product.id} product={product as never} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-stone-300 py-16 text-center">
              <p className="text-stone-500">Catalogue en cours de mise à jour</p>
            </div>
          )}
        </div>
      </section>

      <GoogleReviews />

      {/* Location */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-4">
          <div className="grid gap-8 lg:grid-cols-2">
            <div>
              <h2 className="mb-4 text-2xl font-bold text-stone-900">Nous trouver</h2>
              <div className="space-y-4 text-stone-600">
                <p className="flex items-start gap-3">
                  <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                  <span>
                    <strong className="text-stone-900">{SHOP.fullAddress}</strong>
                  </span>
                </p>
                <p className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-amber-600" />
                  <a href={SHOP.phoneHref} className="font-medium hover:text-amber-700">
                    {SHOP.phone}
                  </a>
                </p>
                <p className="text-sm text-stone-500">{SHOP.hours}</p>
                <a href={SHOP.mapsUrl} target="_blank" rel="noopener noreferrer">
                  <Button>
                    <MapPin className="h-4 w-4" />
                    Obtenir l&apos;itinéraire
                  </Button>
                </a>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl border border-stone-200 shadow-sm">
              <iframe
                src={SHOP.mapsEmbed}
                width="100%"
                height="350"
                style={{ border: 0 }}
                allowFullScreen
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                title="Carte Google Maps"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Age warning */}
      <section className="bg-amber-50 py-6">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-amber-900">
          <Shield className="mx-auto mb-2 h-5 w-5" />
          La vente de produits de vape est strictement réservée aux personnes majeures (+18 ans).
        </div>
      </section>
    </>
  );
}
