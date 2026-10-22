import { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <main className="card">
      <p className="eyebrow">Azure Static Web Apps + React + Vite</p>
      <h1>Your frontend starts here.</h1>
      <p className="intro">
        A lightweight React app, ready to build and publish to Azure.
        No frontend server required in production.
      </p>
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
