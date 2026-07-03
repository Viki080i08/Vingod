import { Suspense } from "react";
import SuccesContent from "./SuccesContent";

export default function SuccesPage() {
  return (
    <Suspense fallback={<div className="py-20 text-center">Chargement...</div>}>
      <SuccesContent />
    </Suspense>
  );
}
