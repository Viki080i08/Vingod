import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const password = await bcrypt.hash("jwell2024", 12);

  const seller = await prisma.seller.upsert({
    where: { email: "vendeur@jwell-fdj.fr" },
    update: {},
    create: {
      email: "vendeur@jwell-fdj.fr",
      password,
      name: "Gérant Jwell FDJ",
    },
  });

  const products = [
    {
      name: "E-liquide Premium Mangue Passion",
      description: "E-liquide fruité aux saveurs de mangue et fruit de la passion. Format 50ml, prêt à vaper.",
      brand: "Jwell",
      category: "E-liquides",
      price: 19.9,
      stock: 25,
      nicotine: "0mg",
      flavor: "Mangue Passion",
      images: JSON.stringify([]),
    },
    {
      name: "Puff X-Bar Blue Razz",
      description: "Puff jetable 800 bouffées, saveur Blue Razz. Prêt à l'emploi, compact et pratique.",
      brand: "X-Bar",
      category: "Puffs",
      price: 8.9,
      stock: 40,
      nicotine: "20mg",
      flavor: "Blue Razz",
      images: JSON.stringify([]),
    },
    {
      name: "Pod Xros 3 Mini",
      description: "Kit pod compact avec batterie intégrée 1000mAh. Idéal pour débuter la vape.",
      brand: "Vaporesso",
      category: "Pods",
      price: 24.9,
      stock: 12,
      images: JSON.stringify([]),
    },
    {
      name: "Résistances GT4 0.15Ω (5pcs)",
      description: "Pack de 5 résistances mesh GT4 pour clearomiseurs Vaporesso. Compatible NRG.",
      brand: "Vaporesso",
      category: "Résistances",
      price: 14.9,
      stock: 30,
      images: JSON.stringify([]),
    },
    {
      name: "E-liquide Menthe Glaciale",
      description: "E-liquide mentholé intense, sensation fraîcheur garantie. Format 10ml.",
      brand: "Jwell",
      category: "E-liquides",
      price: 5.9,
      stock: 3,
      nicotine: "6mg",
      flavor: "Menthe Glaciale",
      images: JSON.stringify([]),
    },
    {
      name: "Chargeur USB-C Universel",
      description: "Câble de charge USB-C pour tous vos appareils de vape.",
      brand: "Jwell",
      category: "Accessoires",
      price: 4.9,
      stock: 50,
      images: JSON.stringify([]),
    },
  ];

  for (const product of products) {
    const existing = await prisma.product.findFirst({
      where: { name: product.name },
    });
    if (!existing) {
      await prisma.product.create({ data: product });
    }
  }

  console.log("Seed terminé !");
  console.log(`Vendeur: ${seller.email} / mot de passe: jwell2024`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
