import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import path from "path";
import { getSellerFromCookie } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  try {
    const formData = await req.formData();
    const files = formData.getAll("files") as File[];

    if (!files.length || files.length > 4) {
      return NextResponse.json(
        { error: "Envoyez entre 1 et 4 images" },
        { status: 400 }
      );
    }

    const uploadDir = path.join(process.cwd(), "public", "uploads");
    await mkdir(uploadDir, { recursive: true });

    const urls: string[] = [];

    for (const file of files) {
      if (!file.type.startsWith("image/")) continue;

      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);
      const filename = `${Date.now()}-${Math.random().toString(36).slice(2)}.${file.name.split(".").pop() || "jpg"}`;
      const filepath = path.join(uploadDir, filename);
      await writeFile(filepath, buffer);
      urls.push(`/uploads/${filename}`);
    }

    return NextResponse.json({ urls });
  } catch {
    return NextResponse.json({ error: "Erreur upload" }, { status: 500 });
  }
}
