/**
 * API Service - handles all HTTP communication with backend
 */
import { HttpClient, HttpEvent, HttpEventType, HttpParams, HttpProgressEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { Document } from '../models/document.model';
import { Entity } from '../models/entity.model';
import { Risk } from '../models/risk.model';

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ChatResponse {
  answer: string;
  entities?: string[];
  evidence?: string[];
  graph_query?: string;
}

export interface GraphQuery {
  query: string;
  entities: Entity[];
  relationships: any[];
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = environment.apiUrl;
  private uploadProgressSubject = new BehaviorSubject<UploadProgress>({ loaded: 0, total: 0, percentage: 0 });

  constructor(private http: HttpClient) {}

  // Upload progress observable
  get uploadProgress$(): Observable<UploadProgress> {
    return this.uploadProgressSubject.asObservable();
  }

  // Document upload with progress tracking
  uploadDocument(file: File): Observable<Document> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<Document>(`${this.baseUrl}/ingest`, formData, {
      reportProgress: true,
      observe: 'events'
    }).pipe(
      map((event: HttpEvent<Document>) => {
        if (event.type === HttpEventType.UploadProgress) {
          const progress = event as HttpProgressEvent;
          const uploadProgress: UploadProgress = {
            loaded: progress.loaded || 0,
            total: progress.total || 0,
            percentage: progress.total ? Math.round((progress.loaded / progress.total) * 100) : 0
          };
          this.uploadProgressSubject.next(uploadProgress);
          return null;
        } else if (event.type === HttpEventType.Response) {
          this.uploadProgressSubject.next({ loaded: 0, total: 0, percentage: 0 });
          return event.body!;
        }
        return null;
      }),
      map(response => response as Document)
    );
  }

  // Document processing pipeline
  extractDocument(documentId: string, schemaName?: string, customSchema?: string): Observable<any> {
    let params = new HttpParams().set('document_id', documentId);
    if (schemaName) params = params.set('schema_name', schemaName);
    if (customSchema) params = params.set('custom_schema', customSchema);
    return this.http.post(`${this.baseUrl}/extract`, null, { params });
  }

  normalizeDocument(documentId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/normalize`, null, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  indexGraph(graphId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/index`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  detectRisks(graphId: string): Observable<Risk[]> {
    return this.http.post<Risk[]>(`${this.baseUrl}/risk`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  // Entity endpoints
  getEntities(): Observable<Entity[]> {
    return this.http.get<Entity[]>(`${this.baseUrl}/entities`);
  }

  getEntity(id: string): Observable<Entity> {
    return this.http.get<Entity>(`${this.baseUrl}/entities/${id}`);
  }

  searchEntities(query: string): Observable<Entity[]> {
    return this.http.get<Entity[]>(`${this.baseUrl}/entities/search?q=${encodeURIComponent(query)}`);
  }

  // Risk endpoints
  getRisks(): Observable<Risk[]> {
    return this.http.get<Risk[]>(`${this.baseUrl}/risks`);
  }

  getRisk(id: string): Observable<Risk> {
    return this.http.get<Risk>(`${this.baseUrl}/risks/${id}`);
  }

  getRisksByEntity(entityId: string): Observable<Risk[]> {
    return this.http.get<Risk[]>(`${this.baseUrl}/risks/entity/${entityId}`);
  }

  // Document endpoints
  getDocuments(): Observable<Document[]> {
    return this.http.get<Document[]>(`${this.baseUrl}/documents`);
  }

  getDocument(id: string): Observable<Document> {
    return this.http.get<Document>(`${this.baseUrl}/documents/${id}`);
  }

  deleteDocument(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/documents/${id}`);
  }

  // Graph endpoints
  getGraph(graphId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/graph/${graphId}`);
  }

  queryGraph(queryText: string, limit: number = 10): Observable<GraphQuery> {
    return this.http.post<GraphQuery>(`${this.baseUrl}/graph/query`, null, {
      params: new HttpParams()
        .set('query_text', queryText)
        .set('limit', limit.toString())
    });
  }

  // Chatbot endpoint with enhanced response
  chat(message: string, graphId?: string, documentId?: string): Observable<ChatResponse> {
    let params = new HttpParams().set('message', message);
    if (graphId) params = params.set('graph_id', graphId);
    if (documentId) params = params.set('document_id', documentId);
    
    return this.http.post<ChatResponse>(`${this.baseUrl}/ask`, null, { params });
  }

  // Evidence endpoint
  getEvidenceUrl(documentId: string, page?: number): string {
    let url = `${this.baseUrl}/evidence/${documentId}`;
    if (page) url += `?page=${page}`;
    return url;
  }

  getEvidence(documentId: string, page?: number): Observable<Blob> {
    const url = page 
      ? `${this.baseUrl}/evidence/${documentId}?page=${page}`
      : `${this.baseUrl}/evidence/${documentId}`;
    return this.http.get(url, { responseType: 'blob' });
  }

  // Extraction progress
  getExtractStatus(documentId: string): Observable<{ status: string; total?: number; completed?: number; failed?: number }> {
    return this.http.get<{ status: string; total?: number; completed?: number; failed?: number }>(`${this.baseUrl}/extract/status`, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  // Extraction SSE stream
  getExtractStream(documentId: string): EventSource {
    const url = `${this.baseUrl}/extract/stream?document_id=${encodeURIComponent(documentId)}`;
    return new EventSource(url);
  }

  // Jobs
  getExtractJobs(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/extract/jobs`);
  }

  getExtractJob(jobId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/extract/jobs/${jobId}`);
  }

  getExtractJobResult(jobId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/extract/jobs/${jobId}/result`);
  }

  getExtractJobResultUrl(jobId: string): string {
    return `${this.baseUrl}/extract/jobs/${jobId}/result`;
  }

  // Analytics endpoints
  getDashboardStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/analytics/dashboard`);
  }

  getRiskTrends(): Observable<any> {
    return this.http.get(`${this.baseUrl}/analytics/risk-trends`);
  }

  // Health check
  healthCheck(): Observable<{ status: string; timestamp: string }> {
    return this.http.get<{ status: string; timestamp: string }>(`${this.baseUrl}/health`);
  }
}