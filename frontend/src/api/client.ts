/** REST fetch wrappers for the FastAPI backend. */

import type { ParseResponse, PriceResponse, BlotterOrder } from '../types';

const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function parseOrder(text: string): Promise<ParseResponse> {
  return request('/parse', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function priceStructure(parsed: ParseResponse): Promise<PriceResponse> {
  return request('/price', {
    method: 'POST',
    body: JSON.stringify({
      underlying: parsed.underlying,
      structure_name: parsed.structure_name,
      legs: parsed.legs,
      stock_ref: parsed.stock_ref,
      delta: parsed.delta,
      price: parsed.price,
      quote_side: parsed.quote_side,
      quantity: parsed.quantity,
    }),
  });
}

export async function parseAndPrice(text: string): Promise<PriceResponse> {
  const parsed = await parseOrder(text);
  return priceStructure(parsed);
}

export async function priceFromTable(req: {
  underlying: string;
  structure_name: string;
  legs: Array<{
    expiry: string;
    strike: number;
    option_type: string;
    side: string;
    quantity: number;
    ratio: number;
  }>;
  stock_ref: number;
  delta: number;
  price: number;
  quote_side: string;
  quantity: number;
}): Promise<PriceResponse> {
  return request('/price', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function getOrders(): Promise<{ orders: BlotterOrder[] }> {
  return request('/orders');
}

export async function addOrder(order: BlotterOrder): Promise<{ orders: BlotterOrder[] }> {
  return request('/orders', {
    method: 'POST',
    body: JSON.stringify(order),
  });
}

export async function updateOrder(
  id: string,
  updates: Record<string, string>,
): Promise<{ order: BlotterOrder }> {
  return request(`/orders/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteOrders(ids: string[]): Promise<{ orders: BlotterOrder[] }> {
  return request('/orders', {
    method: 'DELETE',
    body: JSON.stringify({ ids }),
  });
}

export async function toggleSource(): Promise<{
  source: string;
  connected: boolean;
  error?: string;
}> {
  return request('/toggle-source', { method: 'POST' });
}

export async function getHealth(): Promise<{ source: string; status: string }> {
  return request('/health');
}
