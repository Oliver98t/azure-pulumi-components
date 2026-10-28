export async function apiRequest(url, options = {}) {
  const headers = new Headers(options.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`.trim(),
    );
  }

  if (response.status === 204 || response.status === 205) {
    return undefined;
  }

  return response.json();
}
