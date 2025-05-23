import { useState, useEffect, useRef } from 'react'
import './App.css'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

function App() {
  const [url, setUrl] = useState('')
  const [email, setEmail] = useState('')
  const [targetPrice, setTargetPrice] = useState('')
  const [loading, setLoading] = useState(false)
  const [product, setProduct] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')

  const pollInterval = 60 * 60 * 1000; 
  const pollRef = useRef();

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setProduct(null)
    setHistory([])
    try {
      const res = await fetch('http://localhost:3000/api/products/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, email, target_price: targetPrice })
      })
      let data
      const contentType = res.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        data = await res.json()
      } else {
        const text = await res.text()
        console.error('Non-JSON response from /api/products/track:', text)
        throw new Error('Sorry, something went wrong. Please try again later.')
      }
      if (!res.ok) throw new Error(data.error || 'Failed to track product')
      setProduct(data.product)
      const histRes = await fetch(`http://localhost:3000/api/products/history/${data.product.id}`)
      let histData
      const histContentType = histRes.headers.get('content-type')
      if (histContentType && histContentType.includes('application/json')) {
        histData = await histRes.json()
      } else {
        const text = await histRes.text()
        console.error('Non-JSON response from /api/products/history:', text)
        throw new Error('Sorry, could not load price history. Please try again later.')
      }
      setHistory(histData.history || [])
    } catch (err) {
      setError(err.message || 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    if (!product || !product.id) return;
    function fetchLatest() {
      fetch(`http://localhost:3000/api/products/${product.id}`)
        .then(res => res.json())
        .then(data => {
          if (data.product) setProduct(data.product);
        });
      fetch(`http://localhost:3000/api/products/history/${product.id}`)
        .then(res => res.json())
        .then(histData => setHistory(histData.history || []));
    }
    pollRef.current = setInterval(fetchLatest, pollInterval);
    return () => clearInterval(pollRef.current);
  }, [product]);

  return (
    <div className="container">
      <h1 style={{ color: '#646cff', marginBottom: 10 }}>Amazon Price Tracker</h1>
      <form onSubmit={handleSubmit} className="track-form" style={{
        background: '#f4f6fb',
        borderRadius: 12,
        boxShadow: '0 2px 12px rgba(100,108,255,0.08)',
        padding: 24,
        maxWidth: 420,
        margin: '0 auto 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16
      }}>
        <input
          type="text"
          placeholder="Enter Amazon product URL"
          value={url}
          onChange={e => setUrl(e.target.value)}
          required
          style={{ padding: 10, borderRadius: 6, border: '1px solid #ccc', fontSize: 16 }}
        />
        <input
          type="email"
          placeholder="Email (optional)"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={{ padding: 10, borderRadius: 6, border: '1px solid #ccc', fontSize: 16 }}
        />
        <input
          type="number"
          placeholder="Target Price (optional)"
          value={targetPrice}
          onChange={e => setTargetPrice(e.target.value)}
          style={{ padding: 10, borderRadius: 6, border: '1px solid #ccc', fontSize: 16 }}
        />
        <button type="submit" disabled={loading} style={{
          background: '#646cff',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          padding: '12px 0',
          fontWeight: 600,
          fontSize: 18,
          cursor: loading ? 'not-allowed' : 'pointer',
          marginTop: 8
        }}>{loading ? 'Tracking...' : 'Track Product'}</button>
      </form>
      {error && <div className="error" style={{ color: '#d32f2f', background: '#fff0f0', borderRadius: 6, padding: 12, margin: '12px auto', maxWidth: 420 }}>{error}</div>}
      {product && (
        <div className="product-preview" style={{
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(100,108,255,0.08)',
          padding: 24,
          maxWidth: 420,
          margin: '0 auto 24px',
          textAlign: 'left',
        }}>
          <h2 style={{ color: '#333', fontSize: 22, marginBottom: 8 }}>{product.title}</h2>
          {product.image && <img src={product.image} alt={product.title} style={{ maxWidth: 180, borderRadius: 8, marginBottom: 12 }} />}
          <p style={{ fontSize: 18, margin: '8px 0', color: '#1a237e', fontWeight: 600 }}>Current Price: <b style={{ color: '#00b894' }}>₹{product.current_price || product.price}</b></p>
          {product.target_price && <p style={{ fontSize: 16, margin: '8px 0', color: '#374151', fontWeight: 500 }}>Target Price: <b style={{ color: '#ff9800' }}>₹{product.target_price}</b></p>}
          {typeof product.email_sent !== 'undefined' && (
            <p style={{ fontSize: 16, margin: '8px 0', color: '#374151', fontWeight: 500 }}>Status: <b style={{ color: product.email_sent ? '#00b894' : '#d32f2f', background: product.email_sent ? '#e8f5e9' : '#ffebee', borderRadius: 4, padding: '2px 8px' }}>{product.email_sent ? 'Mail Sent' : 'Mail Not Sent'}</b></p>
          )}
        </div>
      )}
      {product && product.alternate_prices && product.alternate_prices.length > 0 && (
        <div className="alternate-prices-table" style={{
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(100,108,255,0.08)',
          padding: 24,
          maxWidth: 600,
          margin: '0 auto 24px',
        }}>
          <h3 style={{ color: '#333', marginBottom: 12 }}>Alternate Prices (Flipkart, Meesho, Reliance Digital)</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: '#f4f6fb' }}>
                <th style={{ padding: 8, border: '1px solid #eee' }}>Platform</th>
                <th style={{ padding: 8, border: '1px solid #eee' }}>Title</th>
                <th style={{ padding: 8, border: '1px solid #eee' }}>Price</th>
                <th style={{ padding: 8, border: '1px solid #eee' }}>Link</th>
              </tr>
            </thead>
            <tbody>
              {product.alternate_prices.map((alt, i) => (
                <tr key={i}>
                  <td style={{ padding: 8, border: '1px solid #eee', textTransform: 'capitalize' }}>{alt.platform}</td>
                  <td style={{ padding: 8, border: '1px solid #eee' }}>{alt.title}</td>
                  <td style={{ padding: 8, border: '1px solid #eee' }}>{alt.price || '-'}</td>
                  <td style={{ padding: 8, border: '1px solid #eee' }}>
                    <a href={alt.url} target="_blank" rel="noopener noreferrer">View</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {history.length > 0 && (
        <div className="history-graph" style={{
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(100,108,255,0.08)',
          padding: 24,
          maxWidth: 600,
          margin: '0 auto',
        }}>
          <h3 style={{ color: '#333', marginBottom: 16 }}>Price History</h3>
          <Line
            data={{
              labels: history.map(h => new Date(h.checked_at).toLocaleDateString()),
              datasets: [
                {
                  label: 'Price (₹)',
                  data: history.map(h => h.price),
                  borderColor: '#646cff',
                  backgroundColor: 'rgba(100,108,255,0.2)',
                  tension: 0.3,
                  fill: true
                }
              ]
            }}
            options={{
              responsive: true,
              plugins: {
                legend: { display: false },
                title: { display: false }
              },
              scales: {
                y: { beginAtZero: false }
              }
            }}
          />
        </div>
      )}
    </div>
  )
}

export default App
