const express = require('express');
const app = express();
const cors = require('cors');
const productRoutes = require('./routes/productRoutes');


require('dotenv').config();
const pool = require('./db');

app.use(cors());
app.use(express.json());

app.use('/api/products', productRoutes);
const PORT = process.env.PORT || 3000;
pool.connect()
  .then(client => {
    client.query('SELECT NOW()', (err, res) => {
      client.release();
      if (err) {
        console.error('Unable to connect to the database:', err);
      } else {
        console.log('Connected to PostgreSQL database at', res.rows[0].now);
        app.listen(PORT, () => {
          console.log(`Express server running on port ${PORT}`);
        });
      }
    });
  });