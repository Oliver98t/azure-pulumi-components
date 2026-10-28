import { useEffect, useState } from 'react';
import { apiRequest } from './api.js';

export default function App() {
  const [count, setCount] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function handleLoad() {
      try {
        let baseUrl;
        if(import.meta.env.VITE_ENV == "local") {
          baseUrl = import.meta.env.VITE_API_BE_LOCAL_URL;
        }
        else {
          baseUrl = import.meta.env.VITE_API_BE_DEV_URL;
        }
        
        console.log(baseUrl)
        if (!baseUrl) {
          throw new Error('Set VITE_API_BASE_URL to the backend URL and restart or rebuild the frontend.');
        }

        const data = await apiRequest(`${baseUrl.replace(/\/+$/, '')}/check`, {
          signal: controller.signal,
        });
        console.log(data)
        if (typeof data?.message !== 'string') {
          throw new Error('The API response must contain a message string.');
        }
        if (!controller.signal.aborted) {
          setMessage(data.message);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'API request failed');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    handleLoad();
    return () => controller.abort();
  }, []);

  return (
    <main className="card">
      <p className="eyebrow">Azure Static Web Apps + React + Vite</p>
      <h1>Your frontend starts here.</h1>
      <p className="intro">
        A lightweight React app, ready to build and publish to Azure.
        No frontend server required in production.
      </p>
      <p role="status">{loading ? 'Loading API greeting...' : message}</p>
      {error && <p role="alert">{error}</p>}
      <button
        id="counter"
        type="button"
        onClick={() => setCount((current) => current + 1)}
      >
        Count: {count}
      </button>
      <p id="counter-status" className="hint" role="status">
        {count === 0
          ? 'Click the button to try a little browser-side interactivity.'
          : `You clicked ${count} ${count === 1 ? 'time' : 'times'}.`}
      </p>
      <a
        href="https://learn.microsoft.com/azure/static-web-apps/"
        target="_blank"
        rel="noopener noreferrer"
      >
        Explore Azure Static Web Apps &rarr;
      </a>
    </main>
  );
}
