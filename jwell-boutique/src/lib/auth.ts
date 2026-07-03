import { NextRequest } from "next/server";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "jwell-dev-secret-change-in-production";

export interface SellerToken {
  sellerId: string;
  email: string;
}

export function signToken(payload: SellerToken): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: "7d" });
}

export function verifyToken(token: string): SellerToken | null {
  try {
    return jwt.verify(token, JWT_SECRET) as SellerToken;
  } catch {
    return null;
  }
}

export function getSellerFromRequest(req: NextRequest): SellerToken | null {
  const auth = req.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  return verifyToken(auth.slice(7));
}

export function getSellerFromCookie(req: NextRequest): SellerToken | null {
  const token = req.cookies.get("seller_token")?.value;
  if (!token) return null;
  return verifyToken(token);
}
