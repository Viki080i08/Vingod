import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";
import { signToken } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const { email, password } = await req.json();

    if (!email || !password) {
      return NextResponse.json({ error: "Email et mot de passe requis" }, { status: 400 });
    }

    const seller = await prisma.seller.findUnique({ where: { email } });
    if (!seller || !(await bcrypt.compare(password, seller.password))) {
      return NextResponse.json({ error: "Identifiants incorrects" }, { status: 401 });
    }

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
