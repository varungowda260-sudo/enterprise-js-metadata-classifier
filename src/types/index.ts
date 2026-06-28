// Types for JavaScript Metadata Classification System

export interface ProcessingStats {
  total_files_found: number;
  files_processed: number;
  files_remaining: number;
  valid_records: number;
  cancelled_records: number;
  files_with_errors: number;
  unique_systems: number;
  elapsed_seconds: number;
  estimated_remaining_seconds: number;
  files_per_second: number;
  status: ProcessingStatus;
  current_file: string;
  current_system: string;
  current_status: string;
}

export type ProcessingStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'cancelled'
  | 'error';

export interface ClassificationResult {
  sys_name: string;
  total_records: number;
  unique_note_count: number;
  note_unids: string[];
}

export interface LogEntry {
  timestamp: string;
  file_name: string;
  action: string;
  status: string;
  error_message: string;
}

export interface SkippedFile {
  file_name: string;
  reason: string;
}

export interface FilterRule {
  field: string;
  operator: string;
  value: string;
  action: string;
  case_sensitive: boolean;
  description?: string;
}

export interface UploadResponse {
  filename: string;
  extract_dir: string;
  total_files: number;
  message: string;
}

export interface ProcessResponse {
  status: string;
  stats: ProcessingStats;
  valid_records: number;
  cancelled_records: number;
  skipped_files: number;
  unique_systems: number;
}

export interface SearchQuery {
  sys_name?: string;
  note_unid?: string;
  status?: string;
}

export interface ParserTestResult {
  file_name: string;
  note_unid: string;
  sys_name: string;
  status: string;
  parser_status: 'PASS' | 'FAIL';
  missing_fields: string[];
  details: {
    note_unid_found: boolean;
    sys_name_found: boolean;
    status_found: boolean;
  };
}
