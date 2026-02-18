/** TypeScript interfaces mirroring the FastAPI Pydantic schemas. */

export interface LegRow {
  leg: string;
  expiry: string;
  strike: number | string;
  type: string;
  ratio: number | string;
  bid_size: string;
  bid: string;
  mid: string;
  offer: string;
  offer_size: string;
}

export interface OrderHeader {
  underlying: string;
  structure_name: string;
  stock_ref: number;
  stock_price: number;
  delta: number;
}

export interface BrokerQuote {
  broker_price: number;
  quote_side: string;
  screen_mid: number | null;
  edge: number | null;
}

export interface CurrentStructure {
  underlying: string;
  structure_name: string;
  structure_detail: string;
  bid: number | null;
  mid: number | null;
  offer: number | null;
  bid_size: number | null;
  offer_size: number | null;
  multiplier: number;
}

export interface PriceResponse {
  table_data: LegRow[];
  header: OrderHeader;
  broker_quote: BrokerQuote | null;
  current_structure: CurrentStructure;
}

export interface ParsedLeg {
  underlying: string;
  expiry: string;
  strike: number;
  option_type: string;
  side: string;
  quantity: number;
  ratio: number;
}

export interface ParseResponse {
  underlying: string;
  structure_name: string;
  legs: ParsedLeg[];
  stock_ref: number;
  delta: number;
  price: number;
  quote_side: string;
  quantity: number;
  raw_text: string;
}

export interface BlotterOrder {
  id: string;
  added_time: string;
  underlying: string;
  structure: string;
  bid: string;
  mid: string;
  offer: string;
  bid_size: string;
  offer_size: string;
  side: string;
  size: string;
  traded: string;
  bought_sold: string;
  traded_price: string;
  initiator: string;
  pnl: string;
  multiplier: number;
  // Recall data
  _table_data?: LegRow[];
  _underlying?: string;
  _structure_type?: string;
  _stock_ref?: number;
  _delta?: number;
  _broker_price?: number;
  _quote_side?: string;
  _quantity?: number;
  _current_structure?: CurrentStructure;
}

export interface HealthData {
  source: string;
  status: string;
}

export interface StructureTemplate {
  label: string;
  value: string;
}
