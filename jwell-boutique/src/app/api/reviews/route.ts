import { NextResponse } from "next/server";
import { getGoogleReviews } from "@/lib/google-reviews";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = await getGoogleReviews();
  return NextResponse.json(data);
}
