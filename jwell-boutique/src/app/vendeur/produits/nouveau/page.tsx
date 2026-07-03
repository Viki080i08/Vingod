"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Camera, PenLine, Upload, Sparkles, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input, Textarea, Select } from "@/components/ui/Input";
import { CATEGORIES } from "@/lib/utils";
import { SellerNav } from "@/components/SellerNav";

type Mode = "choose" | "manual" | "photo";

interface FormData {
  name: string;
  description: string;
  brand: string;
  category: string;
  price: string;
  stock: string;
  nicotine: string;
  flavor: string;
  images: string[];
}

const emptyForm: FormData = {
  name: "",
  description: "",
  brand: "",
  category: "Autre",
  price: "",
  stock: "0",
  nicotine: "",
  flavor: "",
  images: [],
};

export default function NouveauProduitPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("choose");
  const [form, setForm] = useState<FormData>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [aiMessage, setAiMessage] = useState("");

  const updateForm = (field: keyof FormData, value: string | string[]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handlePhotoUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (files.length > 4) {
      setError("Maximum 4 photos");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      Array.from(files).forEach((f) => formData.append("files", f));

      const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
      const uploadData = await uploadRes.json();
      if (!uploadRes.ok) throw new Error(uploadData.error);

      const urls = uploadData.urls;
      updateForm("images", urls);

      setAnalyzing(true);
      const baseUrl = window.location.origin;
      const fullUrls = urls.map((u: string) => `${baseUrl}${u}`);

      const analyzeRes = await fetch("/api/products/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ images: fullUrls }),
      });
      const analyzeData = await analyzeRes.json();

      if (analyzeData.analyzed) {
        const a = analyzeData.analyzed;
        setForm((prev) => ({
          ...prev,
          name: a.name || prev.name,
          description: a.description || prev.description,
          brand: a.brand || prev.brand,
          category: CATEGORIES.includes(a.category) ? a.category : "Autre",
          price: a.price ? String(a.price) : prev.price,
          nicotine: a.nicotine || prev.nicotine,
          flavor: a.flavor || prev.flavor,
          images: urls,
        }));
        if (analyzeData.message) setAiMessage(analyzeData.message);
      }

      setMode("manual");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur upload");
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price),
          stock: parseInt(form.stock, 10),
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      router.push("/vendeur/produits");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur création");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-100">
      <SellerNav active="produits" onLogout={() => router.push("/vendeur/login")} />

      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Ajouter un produit</h1>

        {mode === "choose" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <button
              onClick={() => setMode("manual")}
              className="flex flex-col items-center gap-3 rounded-xl border-2 border-stone-200 bg-white p-8 transition-colors hover:border-amber-500 hover:bg-amber-50"
            >
              <PenLine className="h-10 w-10 text-amber-600" />
              <div className="text-center">
                <p className="font-semibold">Saisie manuelle</p>
                <p className="text-sm text-stone-500">Remplir le formulaire vous-même</p>
              </div>
            </button>
            <button
              onClick={() => setMode("photo")}
              className="flex flex-col items-center gap-3 rounded-xl border-2 border-stone-200 bg-white p-8 transition-colors hover:border-amber-500 hover:bg-amber-50"
            >
              <Camera className="h-10 w-10 text-amber-600" />
              <div className="text-center">
                <p className="font-semibold">Via photos (1 à 4)</p>
                <p className="text-sm text-stone-500">L&apos;IA remplit le formulaire automatiquement</p>
              </div>
            </button>
          </div>
        )}

        {mode === "photo" && (
          <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => handlePhotoUpload(e.target.files)}
            />
            <Upload className="mx-auto mb-4 h-12 w-12 text-amber-600" />
            <h2 className="mb-2 text-lg font-semibold">Uploadez 1 à 4 photos</h2>
            <p className="mb-6 text-sm text-stone-500">
              Prenez des photos du produit (face, dos, étiquette...) et l&apos;IA remplira le formulaire
            </p>
            <Button onClick={() => fileRef.current?.click()} disabled={loading || analyzing}>
              {analyzing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Analyse IA en cours...
                </>
              ) : loading ? (
                "Upload en cours..."
              ) : (
                <>
                  <Camera className="h-4 w-4" />
                  Choisir des photos
                </>
              )}
            </Button>
            <button
              onClick={() => setMode("choose")}
              className="mt-4 block w-full text-sm text-stone-400 hover:text-stone-600"
            >
              ← Retour
            </button>
          </div>
        )}

        {mode === "manual" && (
          <form onSubmit={handleSubmit} className="rounded-xl border border-stone-200 bg-white p-6">
            {aiMessage && (
              <div className="mb-4 flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
                {aiMessage}
              </div>
            )}

            {form.images.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {form.images.map((img, i) => (
                  <div key={i} className="relative h-20 w-20 overflow-hidden rounded-lg">
                    <Image src={img} alt="" fill className="object-cover" />
                    <button
                      type="button"
                      onClick={() =>
                        updateForm(
                          "images",
                          form.images.filter((_, j) => j !== i)
                        )
                      }
                      className="absolute right-0 top-0 rounded-bl bg-red-500 p-0.5 text-white"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">Nom du produit *</label>
                <Input value={form.name} onChange={(e) => updateForm("name", e.target.value)} required />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Description</label>
                <Textarea
                  value={form.description}
                  onChange={(e) => updateForm("description", e.target.value)}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Marque</label>
                  <Input value={form.brand} onChange={(e) => updateForm("brand", e.target.value)} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Catégorie</label>
                  <Select value={form.category} onChange={(e) => updateForm("category", e.target.value)}>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Prix (€) *</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price}
                    onChange={(e) => updateForm("price", e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Stock *</label>
                  <Input
                    type="number"
                    min="0"
                    value={form.stock}
                    onChange={(e) => updateForm("stock", e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Nicotine</label>
                  <Input
                    placeholder="ex: 0mg, 3mg, 6mg"
                    value={form.nicotine}
                    onChange={(e) => updateForm("nicotine", e.target.value)}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Saveur</label>
                  <Input value={form.flavor} onChange={(e) => updateForm("flavor", e.target.value)} />
                </div>
              </div>
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <div className="mt-6 flex gap-3">
              <Button type="button" variant="outline" onClick={() => setMode("choose")}>
                Retour
              </Button>
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? "Enregistrement..." : "Publier le produit"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
