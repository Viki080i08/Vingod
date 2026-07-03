import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const email = process.env.SELLER_EMAIL || "vendeur@jwell-fdj.fr";

  await prisma.seller.upsert({
    where: { email },
    update: { name: "Gérant Jwell FDJ" },
    create: {
      email,
      password: "code-auth",
      name: "Gérant Jwell FDJ",
    },
  });

  console.log(`Compte vendeur prêt : ${email}`);
  console.log(`Code d'accès : ${process.env.SELLER_CODE || "123456789"}`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
