import Link from "next/link";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function AnnulePage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-20 text-center">
      <XCircle className="mx-auto mb-4 h-16 w-16 text-red-400" />
      <h1 className="mb-2 text-2xl font-bold text-stone-900">Paiement annulé</h1>
      <p className="mb-8 text-stone-600">
        Votre paiement a été annulé. Votre panier est toujours disponible.
      </p>
      <div className="flex justify-center gap-3">
        <Link href="/panier">
          <Button>Retour au panier</Button>
        </Link>
        <Link href="/produits">
          <Button variant="outline">Voir les produits</Button>
        </Link>
      </div>
    </div>
  );
}
