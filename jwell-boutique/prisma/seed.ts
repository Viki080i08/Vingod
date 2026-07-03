import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const email = process.env.SELLER_EMAIL || "vendeur@jwell-fdj.fr";
  const password = process.env.SELLER_PASSWORD;

  if (!password) {
    console.log("SELLER_PASSWORD non défini — compte vendeur non créé.");
    console.log("Définissez SELLER_EMAIL et SELLER_PASSWORD dans .env puis relancez.");
    return;
  }

  const hashed = await bcrypt.hash(password, 12);

  await prisma.seller.upsert({
    where: { email },
    update: { password: hashed },
    create: {
      email,
      password: hashed,
      name: "Gérant Jwell FDJ",
    },
  });

  console.log(`Compte vendeur configuré : ${email}`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
