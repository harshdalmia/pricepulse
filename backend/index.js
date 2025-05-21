const express = require('express');
const app = express();
const productRoutes = require('./routes/productRoutes');
require('dotenv').config();

app.use(express.json());
app.use('/api/products', productRoutes);
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Express server running on port ${PORT}`);
});