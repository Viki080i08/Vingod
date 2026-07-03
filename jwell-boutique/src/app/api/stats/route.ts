import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSellerFromCookie } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  const [
    totalProducts,
    activeProducts,
    lowStockProducts,
    totalOrders,
    paidOrders,
    revenue,
    recentOrders,
    lowStock,
  ] = await Promise.all([
    prisma.product.count(),
    prisma.product.count({ where: { isActive: true } }),
    prisma.product.count({ where: { stock: { lte: 5 }, isActive: true } }),
    prisma.order.count(),
    prisma.order.count({ where: { status: { in: ["PAID", "PREPARING", "READY", "COMPLETED"] } } }),
    prisma.order.aggregate({
      where: { status: { in: ["PAID", "PREPARING", "READY", "COMPLETED"] } },
      _sum: { totalAmount: true },
    }),
    prisma.order.findMany({
      take: 5,
      orderBy: { createdAt: "desc" },
      include: { items: { include: { product: true } } },
    }),
    prisma.product.findMany({
      where: { stock: { lte: 5 }, isActive: true },
      take: 10,
      orderBy: { stock: "asc" },
    }),
  ]);

  return NextResponse.json({
    stats: {
      totalProducts,
      activeProducts,
      lowStockProducts,
      totalOrders,
      paidOrders,
      revenue: revenue._sum.totalAmount || 0,
      recentOrders,
      lowStock,
    },
  });
}
