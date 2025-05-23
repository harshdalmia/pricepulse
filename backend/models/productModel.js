const db = require('../db');

async function createOrUpdateProduct({ url, title, image, price, email, targetPrice, metadata }) {
  const res = await db.query(`
    INSERT INTO products (url, title, image, current_price, user_email, target_price, metadata)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (url) DO UPDATE SET
      title = EXCLUDED.title,
      image = EXCLUDED.image,
      current_price = EXCLUDED.current_price,
      metadata = COALESCE(EXCLUDED.metadata, products.metadata)
    RETURNING *;
  `, [url, title, image, price, email, targetPrice, metadata ? JSON.stringify(metadata) : null]);

  return res.rows[0];
}

async function insertPriceHistory(productId, price) {
  return db.query(`
    INSERT INTO price_history (product_id, price)
    VALUES ($1, $2);
  `, [productId, price]);
}

async function getAllTrackedProducts() {
  const res = await db.query(`SELECT * FROM products`);
  return res.rows;
}

async function getProductById(productId) {
 
  const prodRes = await db.query('SELECT * FROM products WHERE id = $1', [productId]);
  if (prodRes.rows.length === 0) return null;
  const product = prodRes.rows[0];

  if (product.metadata && typeof product.metadata === 'string') {
    try {
      product.metadata = JSON.parse(product.metadata);
    } catch (e) {
   
    }
  }
  const histRes = await db.query(
    'SELECT email_sent FROM price_history WHERE product_id = $1 ORDER BY checked_at DESC LIMIT 1',
    [productId]
  );
  product.email_sent = histRes.rows.length > 0 ? histRes.rows[0].email_sent : false;
  return product;
}
async function insertAlternatePrices(productId, alternates, platform) {
  if (!Array.isArray(alternates)) return;
  for (const alt of alternates) {
    await db.query(
      `INSERT INTO alternate_prices (product_id, platform, title, url, price)
       VALUES ($1, $2, $3, $4, $5)`,
      [productId, platform, alt.title, alt.url, alt.price ? parseFloat(alt.price.replace(/[^\d.]/g, '')) : null]
    );
  }
}

async function getAlternatePrices(productId) {
  const res = await db.query(
    'SELECT platform, title, url, price, scraped_at FROM alternate_prices WHERE product_id = $1 ORDER BY scraped_at DESC',
    [productId]
  );
  return res.rows;
}

module.exports = {
  createOrUpdateProduct,
  insertPriceHistory,
  getAllTrackedProducts,
  getProductById,
  insertAlternatePrices,
  getAlternatePrices
};
