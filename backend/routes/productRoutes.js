const express = require('express');
const router = express.Router();
const { runPriceCheck } = require('../scheduler/jobScheduler');
const { scrapeProduct } = require('../services/scraperServices');
const { createOrUpdateProduct } = require('../models/productModel');

router.post('/track', async (req, res) => {
  const { url, email, target_price } = req.body;

  try {
    
    const scraped = await scrapeProduct(url);
    if (!scraped || !scraped.title || !scraped.price) {
      return res.status(400).json({ error: 'Failed to scrape product data.' });
    }
  
    const product = await createOrUpdateProduct({
      url,
      title: scraped.title,
      image: scraped.image,
      price: scraped.price,
      email,
      targetPrice: target_price 
    });
    console.log(`[TRACK] Saved product:`, product);
   
    await runPriceCheck();
    res.json({ message: `Tracking started for ${url} and scheduler triggered.`, product });
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

module.exports = router;
