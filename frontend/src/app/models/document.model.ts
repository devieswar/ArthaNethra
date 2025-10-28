/**
 * Document model for frontend
 */
export enum DocumentStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  UPLOADED = 'uploaded',
  EXTRACTING = 'extracting',
  EXTRACTED = 'extracted',
  NORMALIZING = 'normalizing',
  NORMALIZED = 'normalized',
  INDEXING = 'indexing',
  INDEXED = 'indexed',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface Document {
  id: string;
  filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus;
  extraction_id?: string;
  graph_id?: string;
  entities_count: number;
  edges_count: number;
  uploaded_at: string;
  processed_at?: string;
  error_message?: string;
  ade_output?: any;
  confidence_score?: number;
  total_pages?: number;
}

