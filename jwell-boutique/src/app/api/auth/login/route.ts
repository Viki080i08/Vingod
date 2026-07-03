import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { signToken } from "@/lib/auth";

const SELLER_CODE = process.env.SELLER_CODE || "123456789";
const SELLER_EMAIL = process.env.SELLER_EMAIL || "vendeur@jwell-fdj.fr";

async function getOrCreateSeller() {
  let seller = await prisma.seller.findUnique({ where: { email: SELLER_EMAIL } });
  if (!seller) {
    seller = await prisma.seller.create({
      data: {
        email: SELLER_EMAIL,
        password: "code-auth",
        name: "Gérant Jwell FDJ",
      },
    });
  }
  return seller;
}

export async function POST(req: NextRequest) {
  try {
    const { code } = await req.json();

    if (!code) {
      return NextResponse.json({ error: "Code requis" }, { status: 400 });
    }

    if (code.trim() !== SELLER_CODE) {
      return NextResponse.json({ error: "Code incorrect" }, { status: 401 });
    }

    const seller = await getOrCreateSeller();
    const token = signToken({ sellerId: seller.id, email: seller.email });

    const response = NextResponse.json({
      seller: { id: seller.id, email: seller.email, name: seller.name },
    });

    response.cookies.set("seller_token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });

    return response;
  } catch {
    return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
  }
}
