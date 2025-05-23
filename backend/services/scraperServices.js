const axios = require('axios');
const { console } = require('inspector');

async function scrapeProduct(url, extract_metadata = false, get_alternates = true) {
  console.log("Scraping product data from URL:", url);
  const res = await axios.get(`${process.env.SCRAPER_URL}/scrape`, {
    params: { url, extract_metadata, get_alternates }
  });
  return res.data.results;
}

module.exports = { scrapeProduct };
