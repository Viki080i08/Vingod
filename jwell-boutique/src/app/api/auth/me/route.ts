import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSellerFromCookie } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non authentifié" }, { status: 401 });
  }

  const data = await prisma.seller.findUnique({
    where: { id: seller.sellerId },
    select: { id: true, email: true, name: true },
  });

  if (!data) {
    return NextResponse.json({ error: "Vendeur introuvable" }, { status: 404 });
  }

  return NextResponse.json({ seller: data });
}
