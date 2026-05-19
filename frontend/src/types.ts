export type Citation = {
  title: string;
  article?: string;
  snippet: string;
  source_url?: string;
  score: number;
};

export type QueryResponse = {
  answer: string;
  citations: Citation[];
  confidence: number;
  disclaimer: string;
  status: "answered" | "low_confidence";
};

export type ChatLog = {
  id: string;
  query: string;
  answer: string;
  status: string;
  confidence: number;
  citations: Citation[];
  review_status?: string;
  created_at: string;
};

export type DocumentRecord = {
  document_id: string;
  title: string;
  source_url: string;
  document_type: string;
  domain: string;
  effective_status: string;
  enabled: boolean;
  chunks_count: number;
  ingestion_status: string;
  updated_at: string;
};

export type IngestionJob = {
  task_id: string;
  document_id: string;
  status: string;
  file_url: string;
  message: string;
  chunks_indexed: number;
  error?: string;
  started_at: string;
  finished_at?: string;
};

export type AuthUser = {
  token: string;
  username: string;
  role: string;
};
