import assert from 'node:assert/strict';
import { afterEach, mock, test } from 'node:test';
import { apiRequest } from '../src/api.js';

afterEach(() => mock.restoreAll());

test('returns JSON and requests a JSON response by default', async () => {
  const fetchMock = mock.method(globalThis, 'fetch', async () =>
    Response.json({ message: 'Hello from Azure Web App!' }),
  );

  assert.deepEqual(await apiRequest('/check'), {
    message: 'Hello from Azure Web App!',
  });
  const [url, options] = fetchMock.mock.calls[0].arguments;
  assert.equal(url, '/check');
  assert.equal(options.headers.get('Accept'), 'application/json');
});

test('forwards POST bodies, headers, credentials, and cancellation signals', async () => {
  const fetchMock = mock.method(globalThis, 'fetch', async () =>
    Response.json({ id: 1 }),
  );
  const controller = new AbortController();
  const options = {
    method: 'POST',
    headers: new Headers({
      'Content-Type': 'application/json',
      Accept: 'application/problem+json',
      Authorization: 'Bearer test-token',
    }),
    body: JSON.stringify({ name: 'example' }),
    credentials: 'include',
    signal: controller.signal,
  };

  await apiRequest('/items', options);
  const forwarded = fetchMock.mock.calls[0].arguments[1];
  assert.equal(forwarded.method, options.method);
  assert.equal(forwarded.body, options.body);
  assert.equal(forwarded.credentials, options.credentials);
  assert.equal(forwarded.signal, options.signal);
  assert.equal(forwarded.headers.get('Content-Type'), 'application/json');
  assert.equal(forwarded.headers.get('Accept'), 'application/problem+json');
  assert.equal(forwarded.headers.get('Authorization'), 'Bearer test-token');
});

for (const status of [204, 205]) {
  test(`returns undefined for an empty ${status} response`, async () => {
    mock.method(globalThis, 'fetch', async () => new Response(null, { status }));
    assert.equal(await apiRequest('/items'), undefined);
  });
}

test('throws on unsuccessful HTTP responses', async () => {
  mock.method(globalThis, 'fetch', async () =>
    new Response('Unavailable', { status: 503, statusText: 'Service Unavailable' }),
  );
  await assert.rejects(apiRequest('/check'), {
    message: 'API request failed: 503 Service Unavailable',
  });
});

test('propagates network and cancellation errors', async () => {
  for (const error of [
    new TypeError('Failed to fetch'),
    new DOMException('Request cancelled', 'AbortError'),
  ]) {
    mock.method(globalThis, 'fetch', async () => { throw error; });
    await assert.rejects(apiRequest('/check'), (actual) => actual === error);
    mock.restoreAll();
  }
});

test('rejects malformed JSON rather than returning a successful fallback', async () => {
  mock.method(globalThis, 'fetch', async () => new Response('not JSON'));
  await assert.rejects(apiRequest('/check'), SyntaxError);
});
