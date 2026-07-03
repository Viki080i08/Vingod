import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSellerFromCookie } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  const orders = await prisma.order.findMany({
    include: {
      items: {
        include: { product: true },
      },
    },
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json({ orders });
}

export async function PATCH(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  try {
    const { orderId, status } = await req.json();

    const order = await prisma.order.update({
      where: { id: orderId },
      data: { status },
      include: {
        items: { include: { product: true } },
      },
    });

    return NextResponse.json({ order });
  } catch {
    return NextResponse.json({ error: "Erreur mise à jour commande" }, { status: 500 });
  }
}
