const express = require('express');
const router = express.Router();

router.post('/track', (req, res) => {
  const { url } = req.body;
  res.json({ message: `Tracking started for ${url}` });
});

module.exports = router;
