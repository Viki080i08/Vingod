import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { getSellerFromCookie } from "@/lib/auth";
import { CATEGORIES } from "@/lib/utils";

export async function POST(req: NextRequest) {
  const seller = getSellerFromCookie(req);
  if (!seller) {
    return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
  }

  try {
    const { images } = await req.json();

    if (!images || !Array.isArray(images) || images.length === 0 || images.length > 4) {
      return NextResponse.json(
        { error: "Envoyez entre 1 et 4 images" },
        { status: 400 }
      );
    }

    const apiKey = process.env.OPENAI_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        analyzed: {
          name: "Produit vape",
          description: "Produit de cigarette électronique — complétez les détails",
          brand: "Jwell",
          category: "Autre",
          price: 0,
          nicotine: "",
          flavor: "",
          confidence: 0.3,
        },
        message: "Analyse IA limitée — configurez OPENAI_API_KEY pour une analyse complète",
      });
    }

    const openai = new OpenAI({ apiKey });

    const imageContent = images.map((img: string) => ({
      type: "image_url" as const,
      image_url: { url: img, detail: "high" as const },
    }));

    const response = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `Tu es un expert en produits de cigarette électronique pour une boutique française.
Analyse les photos et extrais les informations du produit.
Réponds UNIQUEMENT en JSON valide avec ce format:
{
  "name": "nom du produit",
  "description": "description détaillée en français",
  "brand": "marque",
  "category": "une parmi: ${CATEGORIES.join(", ")}",
  "price": 0,
  "nicotine": "taux de nicotine si visible (ex: 0mg, 3mg, 6mg)",
  "flavor": "saveur si visible",
  "confidence": 0.0 à 1.0
}
Si le prix n'est pas visible, mets 0. Sois précis sur la marque et le type de produit.`,
        },
        {
          role: "user",
          content: [
            { type: "text", text: "Analyse ce(s) produit(s) de vape et remplis le formulaire:" },
            ...imageContent,
          ],
        },
      ],
      max_tokens: 800,
      response_format: { type: "json_object" },
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      return NextResponse.json({ error: "Analyse échouée" }, { status: 500 });
    }

    const analyzed = JSON.parse(content);
    return NextResponse.json({ analyzed });
  } catch (error) {
    console.error("AI analysis error:", error);
    return NextResponse.json({ error: "Erreur lors de l'analyse IA" }, { status: 500 });
  }
}
