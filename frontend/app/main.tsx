import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { Button } from '@/components/ui/button'
import './index.css'

function App() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBackendData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8000/')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBackendData()
  }, [])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Backend Response</h1>
      
      {loading && <p>Loading...</p>}
      
      {error && (
        <div className="text-red-500 mb-4">
          <p>Error: {error}</p>
        </div>
      )}
      
      {data && (
        <div className="mb-4">
          <h2 className="text-lg font-semibold mb-2">Response:</h2>
          <pre className="bg-gray-100 p-4 rounded">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
      
      <Button onClick={fetchBackendData} disabled={loading}>
        {loading ? 'Loading...' : 'Refresh Data'}
      </Button>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
