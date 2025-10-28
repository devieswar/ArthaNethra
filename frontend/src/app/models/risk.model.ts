/**
 * Risk model for frontend
 */
import { Citation } from './entity.model';

export enum RiskSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface Risk {
  id: string;
  type: string;
  severity: RiskSeverity;
  description: string;
  affected_entity_ids: string[];
  citations: Citation[];
  score: number;
  threshold: number;
  actual_value: number;
  recommendation: string;
  document_id: string;
  graph_id: string;
  detected_at: string;
}

export interface RiskSummary {
  total_risks: number;
  high_severity: number;
  medium_severity: number;
  low_severity: number;
  critical_severity: number;
  risks: Risk[];
}

