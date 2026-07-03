import "dotenv/config";
import { syncGoogleReviews } from "../src/lib/google-reviews";

syncGoogleReviews()
  .then((data) => {
    console.log(`✓ Note : ${data.rating}/5 (${data.reviewCount} avis)`);
    console.log(`✓ ${data.reviews.length} avis récupérés depuis Google`);
  })
  .catch((err) => {
    console.error("Erreur:", err.message);
    process.exit(1);
  });
