/**
 * API Service - handles all HTTP communication with backend
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Document } from '../models/document.model';
import { Graph } from '../models/entity.model';
import { RiskSummary } from '../models/risk.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Document endpoints
  uploadDocument(file: File): Observable<Document> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<Document>(`${this.baseUrl}/ingest`, formData);
  }

  extractDocument(documentId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/extract`, null, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  normalizeDocument(documentId: string): Observable<Graph> {
    return this.http.post<Graph>(`${this.baseUrl}/normalize`, null, {
      params: new HttpParams().set('document_id', documentId)
    });
  }

  indexGraph(graphId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/index`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  detectRisks(graphId: string): Observable<RiskSummary> {
    return this.http.post<RiskSummary>(`${this.baseUrl}/risk`, null, {
      params: new HttpParams().set('graph_id', graphId)
    });
  }

  // Graph endpoints
  getGraph(graphId: string): Observable<Graph> {
    return this.http.get<Graph>(`${this.baseUrl}/graph/${graphId}`);
  }

  queryGraph(queryText: string, limit: number = 10): Observable<any> {
    return this.http.post(`${this.baseUrl}/graph/query`, null, {
      params: new HttpParams()
        .set('query_text', queryText)
        .set('limit', limit.toString())
    });
  }

  // Chatbot endpoint
  chat(message: string, graphId?: string, documentId?: string): Observable<string> {
    let params = new HttpParams().set('message', message);
    if (graphId) params = params.set('graph_id', graphId);
    if (documentId) params = params.set('document_id', documentId);
    
    return this.http.post(`${this.baseUrl}/ask`, null, {
      params,
      responseType: 'text'
    });
  }

  // Evidence endpoint
  getEvidenceUrl(documentId: string, page?: number): string {
    let url = `${this.baseUrl}/evidence/${documentId}`;
    if (page) url += `?page=${page}`;
    return url;
  }
}

