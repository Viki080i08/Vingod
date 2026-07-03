"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useCart } from "@/store/cart";

export default function SuccesContent() {
  const searchParams = useSearchParams();
  const clearCart = useCart((s) => s.clearCart);

  useEffect(() => {
    clearCart();
  }, [clearCart]);

  return (
    <div className="mx-auto max-w-lg px-4 py-20 text-center">
      <CheckCircle className="mx-auto mb-4 h-16 w-16 text-green-500" />
      <h1 className="mb-2 text-2xl font-bold text-stone-900">Commande confirmée !</h1>
      <p className="mb-2 text-stone-600">
        Merci pour votre commande. Vous recevrez un email de confirmation.
      </p>
      {searchParams.get("order_id") && (
        <p className="mb-6 text-sm text-stone-400">
          Référence : {searchParams.get("order_id")}
        </p>
      )}
      <p className="mb-8 text-sm text-stone-500">
        Vous pouvez venir récupérer votre commande en magasin ou nous contacter pour plus
        d&apos;informations.
      </p>
      <div className="flex justify-center gap-3">
        <Link href="/produits">
          <Button variant="outline">Continuer mes achats</Button>
        </Link>
        <Link href="/">
          <Button>Retour à l&apos;accueil</Button>
        </Link>
      </div>
    </div>
  );
}
