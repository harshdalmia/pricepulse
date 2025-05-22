const nodemailer = require('nodemailer');

async function sendPriceDropEmail(to, product, price) {
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS
    }
  });

  const mailOptions = {
    from: process.env.EMAIL_USER,
    to,
    subject: `Price Drop Alert: ${product.title}`,
    text: `Good news! The price for ${product.title} has dropped to ₹${price} (Target: ₹${product.target_price}).\n\nCheck it here: ${product.url}`
  };

  await transporter.sendMail(mailOptions);
}

module.exports = { sendPriceDropEmail };