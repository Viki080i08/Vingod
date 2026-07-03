import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSellerFromCookie } from "@/lib/auth";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const product = await prisma.product.findUnique({ where: { id } });

  if (!product) {
    return NextResponse.json({ error: "Produit introuvable" }, { status: 404 });
  }

  if (!product.isActive) {
    const seller = getSellerFromCookie(req);
    if (!seller) {
      return NextResponse.json({ error: "Produit introuvable" }, { status: 404 });
    }
  }

  return NextResponse.json({ product });
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  const { id } = await params;

  try {
    const body = await req.json();
    const product = await prisma.product.update({
      where: { id },
      data: {
        ...(body.name !== undefined && { name: body.name }),
        ...(body.description !== undefined && { description: body.description }),
        ...(body.brand !== undefined && { brand: body.brand }),
        ...(body.category !== undefined && { category: body.category }),
        ...(body.price !== undefined && { price: parseFloat(body.price) }),
        ...(body.stock !== undefined && { stock: parseInt(body.stock, 10) }),
        ...(body.images !== undefined && { images: JSON.stringify(body.images) }),
        ...(body.nicotine !== undefined && { nicotine: body.nicotine }),
        ...(body.flavor !== undefined && { flavor: body.flavor }),
        ...(body.isActive !== undefined && { isActive: body.isActive }),
      },
    });

    return NextResponse.json({ product });
  } catch {
    return NextResponse.json({ error: "Erreur lors de la mise à jour" }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  const { id } = await params;

  try {
    await prisma.product.delete({ where: { id } });
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json({ error: "Erreur lors de la suppression" }, { status: 500 });
  }
}
