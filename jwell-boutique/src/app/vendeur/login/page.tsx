"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function VendeurLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      router.push("/vendeur/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-stone-900 text-lg font-bold text-white">
            JW
          </div>
          <h1 className="text-2xl font-bold text-stone-900">Espace vendeur</h1>
          <p className="text-stone-500">Gérez vos produits, stocks et ventes</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="mb-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="vendeur@jwell-fdj.fr"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Mot de passe</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            <LogIn className="h-4 w-4" />
            {loading ? "Connexion..." : "Se connecter"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-stone-400">
          <Link href="/" className="hover:text-amber-700">
            ← Retour à la boutique
          </Link>
        </p>
      </div>
    </div>
  );
}
