const express = require('express');
const router = express.Router();
const {startScheduler } = require('../scheduler/jobScheduler');
const { scrapeProduct } = require('../services/scraperServices');
const { createOrUpdateProduct, getProductById } = require('../models/productModel');
const db = require('../db');

router.post('/track', async (req, res) => {
  const { url, email, target_price } = req.body;

  const urlPattern = /^https?:\/\/(www\.)?amazon\.[a-z.]+\//i;
  const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  const targetPriceNum = target_price !== undefined && target_price !== '' ? Number(target_price) : undefined;
  if (!url || !urlPattern.test(url)) {
    return res.status(400).json({ error: 'Invalid or missing Amazon product URL.' });
  }
  if (email && !emailPattern.test(email)) {
    return res.status(400).json({ error: 'Invalid email address.' });
  }
  if (targetPriceNum !== undefined && (isNaN(targetPriceNum) || targetPriceNum <= 0)) {
    return res.status(400).json({ error: 'Target price must be a positive number.' });
  }
  const targetPrice = targetPriceNum;
  try {
    let existingProduct = null;
    try {
      const result = await db.query('SELECT metadata FROM products WHERE url = $1', [url]);
      if (result.rows.length > 0 && result.rows[0].metadata) {
        existingProduct = result.rows[0];
      }
    } catch (e) {  }
    const scraped = await scrapeProduct(url, !existingProduct, true); 
    console.log('[SCRAPER RESULT]', scraped); 
    if (!scraped || !scraped.title || !scraped.price) {
      return res.status(400).json({ error: 'Failed to scrape product data.', details: scraped });
    }
    const product = await createOrUpdateProduct({
      url,
      title: scraped.title,
      image: scraped.image,
      price: scraped.price,
      email: email || null,
      targetPrice: target_price !== undefined && target_price !== '' ? Number(target_price) : null,
      metadata: scraped.metadata || (existingProduct ? existingProduct.metadata : null)
    });
    if (scraped.alternate_prices && scraped.alternate_prices.length > 0) {
      const { insertAlternatePrices } = require('../models/productModel');
   
      for (const alt of scraped.alternate_prices) {
        await insertAlternatePrices(product.id, [alt], alt.platform || 'unknown');
      }
    }
    console.log(`[TRACK] Saved product:`, product);

    await db.query(
      'INSERT INTO price_history (product_id, price) VALUES ($1, $2)',
      [product.id, scraped.price]
    );
    startScheduler(product.id);
    const histRes = await db.query(
      'SELECT email_sent FROM price_history WHERE product_id = $1 ORDER BY checked_at DESC LIMIT 1',
      [product.id]
    );
    const email_sent = histRes.rows.length > 0 ? histRes.rows[0].email_sent : false;

    const { getAlternatePrices } = require('../models/productModel');
    const alternate_prices = await getAlternatePrices(product.id);
    res.json({ message: `Tracking started for ${url}.`, product: { ...product, email_sent, alternate_prices } });
  } catch (error) {
    console.error('Error in /track:', error);
   
    res.status(500).json({ error: 'Failed to track product.' });
  }
});

router.get('/history/:id', async (req, res) => {
  const db = require('../db');
  const productId = req.params.id;
  try {
    const result = await db.query(
      'SELECT price, checked_at FROM price_history WHERE product_id = $1 ORDER BY checked_at ASC',
      [productId]
    );
    res.json({ history: result.rows });
  } catch (error) {
    console.error('Error fetching price history:', error);
    res.status(500).json({ error: 'Failed to fetch price history.' });
  }
});

router.get('/:id', async (req, res) => {
  try {
    const product = await getProductById(req.params.id);
    if (!product) return res.status(404).json({ error: 'Product not found' });
    const { getAlternatePrices } = require('../models/productModel');
    const alternate_prices = await getAlternatePrices(product.id);
    res.json({ product: { ...product, alternate_prices } });
  } catch (error) {
    console.error('Error fetching product by id:', error);
    res.status(500).json({ error: 'Failed to fetch product.' });
  }
});

module.exports = router;
