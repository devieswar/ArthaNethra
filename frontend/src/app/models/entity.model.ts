/**
 * Entity model for frontend
 */
export enum EntityType {
  COMPANY = 'Company',
  SUBSIDIARY = 'Subsidiary',
  LOAN = 'Loan',
  INVOICE = 'Invoice',
  METRIC = 'Metric',
  CLAUSE = 'Clause',
  INSTRUMENT = 'Instrument',
  VENDOR = 'Vendor',
  PERSON = 'Person',
  LOCATION = 'Location'
}

export interface Citation {
  page: number;
  section?: string;
  table_id?: string;
  cell?: string;
  clause?: string;
  confidence?: number;
}

export interface Entity {
  id: string;
  type: EntityType;
  name: string;
  properties: Record<string, any>;
  citations: Citation[];
  document_id: string;
  graph_id: string;
  created_at: string;
  updated_at: string;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
  graph_id: string;
  created_at: string;
}

export interface Graph {
  id: string;
  document_id: string;
  entities: Entity[];
  edges: Edge[];
}

