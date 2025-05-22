const axios = require('axios');
const { console } = require('inspector');

async function scrapeProduct(url) {
  console.log("Scraping product data from URL:", url);
  const res = await axios.get(`${process.env.SCRAPER_URL}/scrape`, {
    params: { url }
  });

  return res.data.results;
}

module.exports = { scrapeProduct };
