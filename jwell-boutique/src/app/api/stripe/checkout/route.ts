import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getStripe } from "@/lib/stripe";

export async function POST(req: NextRequest) {
  try {
    const { items, customerName, customerEmail, customerPhone } = await req.json();

    if (!items?.length || !customerName || !customerEmail) {
      return NextResponse.json({ error: "Données manquantes" }, { status: 400 });
    }

    const productIds = items.map((i: { productId: string }) => i.productId);
    const products = await prisma.product.findMany({
      where: { id: { in: productIds }, isActive: true },
    });

    const orderItems: { productId: string; quantity: number; price: number; name: string }[] = [];
    let totalAmount = 0;

    for (const item of items) {
      const product = products.find((p) => p.id === item.productId);
      if (!product) {
        return NextResponse.json(
          { error: `Produit introuvable: ${item.productId}` },
          { status: 400 }
        );
      }
      if (product.stock < item.quantity) {
        return NextResponse.json(
          { error: `Stock insuffisant pour ${product.name}` },
          { status: 400 }
        );
      }
      orderItems.push({
        productId: product.id,
        quantity: item.quantity,
        price: product.price,
        name: product.name,
      });
      totalAmount += product.price * item.quantity;
    }

    const order = await prisma.order.create({
      data: {
        customerName,
        customerEmail,
        customerPhone: customerPhone || null,
        totalAmount,
        status: "PENDING",
        items: {
          create: orderItems.map((i) => ({
            productId: i.productId,
            quantity: i.quantity,
            price: i.price,
          })),
        },
      },
    });

    const stripe = getStripe();
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "payment",
      customer_email: customerEmail,
      line_items: orderItems.map((item) => ({
        price_data: {
          currency: "eur",
          product_data: {
            name: item.name,
          },
          unit_amount: Math.round(item.price * 100),
        },
        quantity: item.quantity,
      })),
      success_url: `${baseUrl}/commande/succes?session_id={CHECKOUT_SESSION_ID}&order_id=${order.id}`,
      cancel_url: `${baseUrl}/commande/annule?order_id=${order.id}`,
      metadata: {
        orderId: order.id,
      },
    });

    await prisma.order.update({
      where: { id: order.id },
      data: { stripeSessionId: session.id },
    });

    return NextResponse.json({ url: session.url, orderId: order.id });
  } catch (error) {
    console.error("Checkout error:", error);
    return NextResponse.json({ error: "Erreur lors du paiement" }, { status: 500 });
  }
}
