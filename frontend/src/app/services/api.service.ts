/**
 * API Service - handles all HTTP communication with backend
 */
import { HttpClient, HttpEvent, HttpEventType, HttpParams, HttpProgressEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';
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
  private readonly _baseUrl = environment.apiUrl;
  private uploadProgressSubject = new BehaviorSubject<UploadProgress>({ loaded: 0, total: 0, percentage: 0 });

  constructor(private http: HttpClient) {}

  get baseUrl(): string {
    return this._baseUrl;
  }

  // Upload progress observable
  get uploadProgress$(): Observable<UploadProgress> {
    return this.uploadProgressSubject.asObservable();
  }

  // Generic HTTP methods for chat sessions
  get(endpoint: string): Observable<any> {
    return this.http.get(`${this._baseUrl}${endpoint}`);
  }

  post(endpoint: string, body: any): Observable<any> {
    return this.http.post(`${this._baseUrl}${endpoint}`, body);
  }

  put(endpoint: string, body: any): Observable<any> {
    return this.http.put(`${this._baseUrl}${endpoint}`, body);
  }

  delete(endpoint: string): Observable<any> {
    return this.http.delete(`${this._baseUrl}${endpoint}`);
  }

  // Document upload with progress tracking
  uploadDocument(file: File): Observable<Document> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<Document>(`${this._baseUrl}/ingest`, formData, {
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
      filter((response): response is Document => response !== null),
      map(response => response as Document)
    );
  }

  // Document processing pipeline
  extractDocument(
    documentId: string, 
    schemaName?: string, 
    customSchema?: string,
    useAdaptiveSchema?: boolean
  ): Observable<any> {
    let params = new HttpParams().set('document_id', documentId);
    if (schemaName) params = params.set('schema_name', schemaName);
    if (customSchema) params = params.set('custom_schema', customSchema);
    if (useAdaptiveSchema) params = params.set('use_adaptive_schema', 'true');
    return this.http.post(`${this._baseUrl}/extract`, null, { params });
  }

  normalizeDocument(documentId: string): Observable<any> {
    return this.http.post(`${this._baseUrl}/normalize`, null, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  indexGraph(graphId: string): Observable<any> {
    return this.http.post(`${this._baseUrl}/index`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  detectRisks(graphId: string): Observable<Risk[]> {
    return this.http.post<Risk[]>(`${this._baseUrl}/risk`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  // Entity endpoints
  getEntities(): Observable<Entity[]> {
    return this.http.get<Entity[]>(`${this._baseUrl}/entities`);
  }

  getEntity(id: string): Observable<Entity> {
    return this.http.get<Entity>(`${this._baseUrl}/entities/${id}`);
  }

  searchEntities(query: string): Observable<Entity[]> {
    return this.http.get<Entity[]>(`${this._baseUrl}/entities/search?q=${encodeURIComponent(query)}`);
  }

  // Relationship/Edge endpoints
  getRelationships(): Observable<any[]> {
    return this.http.get<any[]>(`${this._baseUrl}/relationships`);
  }

  // Risk endpoints
  getRisks(): Observable<Risk[]> {
    return this.http.get<Risk[]>(`${this._baseUrl}/risks`);
  }

  getRisk(id: string): Observable<Risk> {
    return this.http.get<Risk>(`${this._baseUrl}/risks/${id}`);
  }

  getRisksByEntity(entityId: string): Observable<Risk[]> {
    return this.http.get<Risk[]>(`${this._baseUrl}/risks/entity/${entityId}`);
  }

  // Document endpoints
  getDocuments(): Observable<Document[]> {
    return this.http.get<Document[]>(`${this._baseUrl}/documents`);
  }

  getDocument(id: string): Observable<Document> {
    return this.http.get<Document>(`${this._baseUrl}/documents/${id}`);
  }

  deleteDocument(id: string): Observable<void> {
    return this.http.delete<void>(`${this._baseUrl}/documents/${id}`);
  }

  // Graph endpoints
  getGraph(graphId: string): Observable<any> {
    return this.http.get(`${this._baseUrl}/graph/${graphId}`);
  }

  queryGraph(queryText: string, limit: number = 10): Observable<GraphQuery> {
    return this.http.post<GraphQuery>(`${this._baseUrl}/graph/query`, null, {
      params: new HttpParams()
        .set('query_text', queryText)
        .set('limit', limit.toString())
    });
  }

  // Chatbot endpoint with enhanced response
  chat(message: string, graphId?: string, documentId?: string): Observable<any> {
    let params = new HttpParams()
      .set('message', message)
      .set('stream', 'false');  // Request non-streaming response
    if (graphId) params = params.set('graph_id', graphId);
    if (documentId) params = params.set('document_id', documentId);
    
    return this.http.post<any>(`${this._baseUrl}/ask`, null, { params });
  }
  
  chatStream(message: string, graphId?: string, documentId?: string): Observable<string> {
    return new Observable(observer => {
      let params = new URLSearchParams();
      params.set('message', message);
      params.set('stream', 'true');
      if (graphId) params.set('graph_id', graphId);
      if (documentId) params.set('document_id', documentId);
      
      const eventSource = new EventSource(`${this._baseUrl}/ask?${params.toString()}`);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.done) {
            eventSource.close();
            observer.complete();
          } else if (data.content) {
            observer.next(data.content);
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      };
      
      eventSource.onerror = (error) => {
        eventSource.close();
        observer.error(error);
      };
      
      return () => eventSource.close();
    });
  }

  // Evidence endpoint
  getEvidenceUrl(documentId: string, page?: number): string {
    let url = `${this._baseUrl}/evidence/${documentId}`;
    if (page) url += `?page=${page}`;
    return url;
  }

  getEvidence(documentId: string, page?: number): Observable<Blob> {
    const url = page 
      ? `${this._baseUrl}/evidence/${documentId}?page=${page}`
      : `${this._baseUrl}/evidence/${documentId}`;
    return this.http.get(url, { responseType: 'blob' });
  }

  // Extraction progress
  getExtractStatus(documentId: string): Observable<{ status: string; total?: number; completed?: number; failed?: number }> {
    return this.http.get<{ status: string; total?: number; completed?: number; failed?: number }>(`${this._baseUrl}/extract/status`, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  // Extraction SSE stream
  getExtractStream(documentId: string): EventSource {
    const url = `${this._baseUrl}/extract/stream?document_id=${encodeURIComponent(documentId)}`;
    return new EventSource(url);
  }

  // Jobs
  getExtractJobs(): Observable<any[]> {
    return this.http.get<any[]>(`${this._baseUrl}/extract/jobs`);
  }

  getExtractJob(jobId: string): Observable<any> {
    return this.http.get<any>(`${this._baseUrl}/extract/jobs/${jobId}`);
  }

  getExtractJobResult(jobId: string): Observable<any> {
    return this.http.get<any>(`${this._baseUrl}/extract/jobs/${jobId}/result`);
  }

  getExtractJobResultUrl(jobId: string): string {
    return `${this._baseUrl}/extract/jobs/${jobId}/result`;
  }

  // Analytics endpoints
  getDashboardStats(): Observable<any> {
    return this.http.get(`${this._baseUrl}/analytics/dashboard`);
  }

  getRiskTrends(): Observable<any> {
    return this.http.get(`${this._baseUrl}/analytics/risk-trends`);
  }

  // Health check
  healthCheck(): Observable<{ status: string; timestamp: string }> {
    return this.http.get<{ status: string; timestamp: string }>(`${this._baseUrl}/health`);
  }
}