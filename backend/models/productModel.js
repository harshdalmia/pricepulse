const db = require('../db');

async function createOrUpdateProduct({ url, title, image, price, email, targetPrice }) {
  const res = await db.query(`
    INSERT INTO products (url, title, image, current_price, user_email, target_price)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (url) DO UPDATE SET
      title = EXCLUDED.title,
      image = EXCLUDED.image,
      current_price = EXCLUDED.current_price
    RETURNING *;
  `, [url, title, image, price, email, targetPrice]);

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

module.exports = {
  createOrUpdateProduct,
  insertPriceHistory,
  getAllTrackedProducts
};
