import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSellerFromCookie } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const category = searchParams.get("category");
  const search = searchParams.get("search");
  const includeInactive = searchParams.get("all") === "true";

  const seller = getSellerFromCookie(req);
  const isSeller = !!seller;

  const products = await prisma.product.findMany({
    where: {
      ...(includeInactive && isSeller ? {} : { isActive: true }),
      ...(category && category !== "all" ? { category } : {}),
      ...(search
        ? {
            OR: [
              { name: { contains: search } },
              { brand: { contains: search } },
              { description: { contains: search } },
            ],
          }
        : {}),
    },
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json({ products });
}

export async function POST(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  try {
    const body = await req.json();
    const product = await prisma.product.create({
      data: {
        name: body.name,
        description: body.description || null,
        brand: body.brand || null,
        category: body.category || "Autre",
        price: parseFloat(body.price),
        stock: parseInt(body.stock, 10) || 0,
        images: JSON.stringify(body.images || []),
        nicotine: body.nicotine || null,
        flavor: body.flavor || null,
        isActive: body.isActive !== false,
      },
    });

    return NextResponse.json({ product }, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Erreur lors de la création" }, { status: 500 });
  }
}
