const { scrapeProduct } = require('../services/scraperService');
const { createOrUpdateProduct, insertPriceHistory } = require('../models/productModel');

async function trackProduct(req, res) {
  try {
    const { url, email, target_price } = req.body;
    const data = await scrapeProduct(url);

    if (!data.title || !data.price) {
      return res.status(400).json({ error: "Failed to scrape product" });
    }

    const product = await createOrUpdateProduct({
      url,
      title: data.title,
      image: data.image,
      price: data.price,
      email,
      target_price: target_price
    });

    await insertPriceHistory(product.id, data.price);

    res.json(product);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  }
}

module.exports = { trackProduct };
