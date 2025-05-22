const cron = require('node-cron');
const { getAllTrackedProducts} = require('../models/productModel');
const { scrapeProduct } = require('../services/scraperServices');
const { sendPriceDropEmail } = require('../services/emailServices');
const db = require('../db');

async function runPriceCheck() {
  const now = new Date().toISOString();
  console.log(`[${now}] Scheduler: Running hourly price check...`);

  const products = await getAllTrackedProducts();
  console.log(`[${now}] Scheduler: Found ${products.length} products to check.`);

  for (const product of products) {
    console.log(`[${now}] Scheduler: Sending to scraper: ${product.url}`);
    const scraped = await scrapeProduct(product.url);
    if (scraped.price) {
      
      const result = await db.query(
        'INSERT INTO price_history (product_id, price) VALUES ($1, $2) RETURNING id',
        [product.id, scraped.price]
      );
      const priceHistoryId = result.rows[0].id;
     
      if (
        product.target_price &&
        scraped.price <= product.target_price &&
        product.user_email
      ) {
       
        const emailCheck = await db.query(
          'SELECT email_sent FROM price_history WHERE product_id = $1 AND price = $2 AND email_sent = TRUE',
          [product.id, scraped.price]
        );
        if (emailCheck.rowCount === 0) {
          try {
            await sendPriceDropEmail(product.user_email, product, scraped.price);
            await db.query('UPDATE price_history SET email_sent = TRUE WHERE id = $1', [priceHistoryId]);
            console.log(`[${now}] Scheduler: Sent price drop email to ${product.user_email}`);
          } catch (e) {
            console.error(`[${now}] Scheduler: Failed to send email to ${product.user_email}:`, e);
          }
        }
      }
    }
  }
}

function startScheduler() {
    
    runPriceCheck();
    
    cron.schedule('0 * * * *', runPriceCheck);
}

module.exports = { startScheduler, runPriceCheck };
