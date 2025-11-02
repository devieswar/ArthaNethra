import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Document, DocumentStatus } from '../../models/document.model';
import { ApiService } from '../../services/api.service';
import { OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="max-w-4xl mx-auto space-y-6">
      <!-- Page Header -->
      <div class="card">
        <h2 class="text-2xl font-bold text-gray-900 mb-2">
          📄 Upload Financial Document
        </h2>
        <p class="text-gray-600">
          Upload PDFs, Office docs (DOC, DOCX, PPT, PPTX, ODT, ODP), images (PNG, JPG),
          or ZIPs for AI-powered extraction and analysis.
        </p>
        <div class="mt-4">
          <button routerLink="/documents" class="btn btn-secondary">
            View Documents
          </button>
        </div>
      </div>

      <!-- Upload Zone -->
      <div class="card">
        <div 
          class="border-2 border-dashed rounded-lg p-12 text-center transition-colors"
          [ngClass]="{
            'border-primary-400 bg-primary-50': isDragging,
            'border-gray-300 hover:border-gray-400': !isDragging
          }"
          (dragover)="onDragOver($event)"
          (dragleave)="onDragLeave($event)"
          (drop)="onDrop($event)">
          
          <div *ngIf="!isUploading && !currentDocument">
            <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            <p class="text-lg font-medium text-gray-900 mb-2">
              Drop your file here or click to browse
            </p>
            <p class="text-sm text-gray-500 mb-4">
              Supported formats: PDF, DOC, DOCX, PPT, PPTX, ODT, ODP, PNG, JPG, ZIP (max 100MB)
            </p>
            <input 
              type="file"
              #fileInput
              (change)="onFileSelected($event)"
              accept=".pdf,.doc,.docx,.ppt,.pptx,.odt,.odp,.png,.jpg,.jpeg,.zip"
              class="hidden">
            <button 
              (click)="fileInput.click()"
              class="btn btn-primary">
              Select File
            </button>
          </div>

          <div *ngIf="isUploading" class="flex flex-col items-center">
            <div class="spinner mb-4"></div>
            <p class="text-gray-700 font-medium">Uploading...</p>
          </div>

          <div *ngIf="currentDocument && !isUploading" class="text-left">
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <h3 class="font-semibold text-gray-900 mb-2">
                  ✓ {{ currentDocument.filename }}
                </h3>
                <div class="space-y-2 text-sm">
                  <div class="flex items-center space-x-2">
                    <span class="text-gray-500">Size:</span>
                    <span class="text-gray-900">{{ formatFileSize(currentDocument.file_size) }}</span>
                  </div>
                  <div class="flex items-center space-x-2">
                    <span class="text-gray-500">Status:</span>
                    <span [ngClass]="getStatusClass(currentDocument.status)">
                      {{ currentDocument.status }}
                    </span>
                  </div>
                  <div *ngIf="currentDocument.total_pages" class="flex items-center space-x-2">
                    <span class="text-gray-500">Pages:</span>
                    <span class="text-gray-900">{{ currentDocument.total_pages }}</span>
                  </div>
                </div>
              </div>
              <button 
                (click)="resetUpload()"
                class="text-gray-400 hover:text-gray-600">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Error Message -->
        <div *ngIf="errorMessage" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-sm text-red-800">{{ errorMessage }}</p>
        </div>
      </div>

      <!-- Processing Steps -->
      <div *ngIf="currentDocument" class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          Processing Pipeline
        </h3>
        <div class="space-y-4">
          <!-- Step 1: Upload -->
          <div class="flex items-start space-x-3">
            <div [ngClass]="getStepClass('uploaded')">1</div>
            <div class="flex-1">
              <h4 class="font-medium text-gray-900">Document Uploaded</h4>
              <p class="text-sm text-gray-500">File stored and validated</p>
            </div>
          </div>

          <!-- Step 2: Extract -->
          <div class="flex items-start space-x-3">
            <div [ngClass]="getStepClass('extracted')">2</div>
            <div class="flex-1">
              <h4 class="font-medium text-gray-900">ADE Extraction</h4>
              <p class="text-sm text-gray-500">Extracting entities and citations</p>
              <button 
                *ngIf="canExtract()"
                (click)="startExtraction()"
                [disabled]="isProcessing"
                class="btn btn-primary btn-sm mt-2">
                Start Extraction
              </button>

              <!-- Extraction Summary -->
              <div *ngIf="extractionSummary && currentDocument?.status === 'extracted'" class="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-500">Entities</div>
                  <div class="text-lg font-semibold text-gray-900">{{ extractionSummary.entities }}</div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-500">Tables</div>
                  <div class="text-lg font-semibold text-gray-900">{{ extractionSummary.tables }}</div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-500">Key-Values</div>
                  <div class="text-lg font-semibold text-gray-900">{{ extractionSummary.keyValues }}</div>
                </div>
              </div>

              <!-- Extracted Fields (Key-Values) -->
              <div *ngIf="extractedKeyValues?.length" class="mt-4">
                <h5 class="text-sm font-medium text-gray-900 mb-2">Extracted Fields</h5>
                <div class="overflow-x-auto border rounded-lg">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr *ngFor="let kv of extractedKeyValues">
                        <td class="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">{{ kv.key }}</td>
                        <td class="px-4 py-2 text-sm text-gray-700">
                          <span *ngIf="isPrimitive(kv.value); else jsonTpl">{{ kv.value }}</span>
                          <ng-template #jsonTpl><pre class="text-xs whitespace-pre-wrap">{{ kv.value | json }}</pre></ng-template>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 3: Normalize -->
          <div class="flex items-start space-x-3">
            <div [ngClass]="getStepClass('normalized')">3</div>
            <div class="flex-1">
              <h4 class="font-medium text-gray-900">Graph Normalization</h4>
              <p class="text-sm text-gray-500">Converting to knowledge graph</p>
              <button 
                *ngIf="canNormalize()"
                (click)="startNormalization()"
                [disabled]="isProcessing"
                class="btn btn-primary btn-sm mt-2">
                Normalize Graph
              </button>
            </div>
          </div>

          <!-- Step 4: Index -->
          <div class="flex items-start space-x-3">
            <div [ngClass]="getStepClass('indexed')">4</div>
            <div class="flex-1">
              <h4 class="font-medium text-gray-900">Graph Indexing</h4>
              <p class="text-sm text-gray-500">Indexing in Weaviate and Neo4j</p>
              <button 
                *ngIf="canIndex()"
                (click)="startIndexing()"
                [disabled]="isProcessing"
                class="btn btn-primary btn-sm mt-2">
                Index Graph
              </button>
            </div>
          </div>

          <!-- Step 5: Analyze -->
          <div class="flex items-start space-x-3">
            <div [ngClass]="getStepClass('completed')">5</div>
            <div class="flex-1">
              <h4 class="font-medium text-gray-900">Risk Detection</h4>
              <p class="text-sm text-gray-500">Detecting financial risks</p>
              <button 
                *ngIf="canAnalyze()"
                (click)="startRiskDetection()"
                [disabled]="isProcessing"
                class="btn btn-primary btn-sm mt-2">
                Detect Risks
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div *ngIf="currentDocument?.status === 'completed'" class="card bg-green-50 border-green-200">
        <h3 class="text-lg font-semibold text-green-900 mb-2">
          ✓ Processing Complete
        </h3>
        <p class="text-sm text-green-700 mb-4">
          Your document has been successfully processed. You can now explore the graph, chat with AI, or review risks.
        </p>
        <div class="flex space-x-3">
          <button routerLink="/graph" class="btn btn-primary">
            View Graph
          </button>
          <button routerLink="/chat" class="btn btn-secondary">
            Chat with AI
          </button>
          <button routerLink="/risks" class="btn btn-secondary">
            View Risks
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .btn-sm {
      @apply px-3 py-1 text-sm;
    }
  `]
})
export class UploadComponent implements OnInit {
  isDragging = false;
  isUploading = false;
  isProcessing = false;
  currentDocument?: Document;
  errorMessage?: string;
  extractionSummary?: { entities: number; tables: number; keyValues: number };
  extractedKeyValues?: { key: string; value: unknown }[];

  constructor(private api: ApiService, private route: ActivatedRoute) {}

  ngOnInit() {
    // Resume flow if navigated with a document_id
    this.route.queryParams.subscribe(params => {
      const docId = params['document_id'];
      if (docId) {
        this.loadDocument(docId);
      }
    });
  }

  private loadDocument(docId: string) {
    this.api.getDocument(docId).subscribe({
      next: (doc) => {
        this.currentDocument = doc;
        // If backend returned extraction results, display summary
        const ade = (doc as any).ade_output || ({} as any);
        const meta = ade?.metadata || {};
        if (meta?.total_pages !== undefined) this.currentDocument!.total_pages = meta.total_pages;
        if (meta?.confidence_score !== undefined) this.currentDocument!.confidence_score = meta.confidence_score;
        const entitiesCount = Array.isArray(ade?.entities) ? ade.entities.length : 0;
        const tablesCount = Array.isArray(ade?.tables) ? ade.tables.length : 0;
        const kv = Array.isArray(ade?.key_values) ? ade.key_values : [];
        if (entitiesCount || tablesCount || kv.length) {
          this.extractionSummary = { entities: entitiesCount, tables: tablesCount, keyValues: kv.length };
          this.extractedKeyValues = kv;
        }
      },
      error: () => {
        // If not found, we silently ignore and let user upload anew
      }
    });
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
    }
  }

  uploadFile(file: File) {
    this.errorMessage = undefined;
    this.isUploading = true;

    this.api.uploadDocument(file).subscribe({
      next: (document) => {
        this.currentDocument = document;
        this.isUploading = false;
        this.extractionSummary = undefined;
        this.extractedKeyValues = undefined;
      },
      error: (error) => {
        this.errorMessage = error.error?.detail || 'Upload failed';
        this.isUploading = false;
      }
    });
  }

  startExtraction() {
    if (!this.currentDocument) return;
    
    this.isProcessing = true;
    this.api.extractDocument(this.currentDocument.id).subscribe({
      next: (result) => {
        if (this.currentDocument) {
          this.currentDocument.status = DocumentStatus.EXTRACTED;
          // Populate extraction metadata if available
          const meta = result?.ade_output?.metadata || {};
          this.currentDocument.total_pages = meta.total_pages ?? this.currentDocument.total_pages;
          this.currentDocument.confidence_score = meta.confidence_score ?? this.currentDocument.confidence_score;
          // Show extraction summary counts
          const entitiesCount = Array.isArray(result?.ade_output?.entities) ? result.ade_output.entities.length : (result?.entities_count ?? 0);
          const tablesCount = Array.isArray(result?.ade_output?.tables) ? result.ade_output.tables.length : 0;
          const kvCount = Array.isArray(result?.ade_output?.key_values) ? result.ade_output.key_values.length : 0;
          this.extractionSummary = { entities: entitiesCount, tables: tablesCount, keyValues: kvCount };
          // Store extracted key-values
          this.extractedKeyValues = Array.isArray(result?.ade_output?.key_values) ? result.ade_output.key_values : [];
        }
        this.isProcessing = false;
      },
      error: (error) => {
        this.errorMessage = 'Extraction failed: ' + error.message;
        this.isProcessing = false;
      }
    });
  }

  startNormalization() {
    if (!this.currentDocument) return;
    
    this.isProcessing = true;
    this.api.normalizeDocument(this.currentDocument.id).subscribe({
      next: (graph) => {
        if (this.currentDocument) {
          this.currentDocument.status = DocumentStatus.NORMALIZED;
          this.currentDocument.graph_id = graph.graph_id;
          this.currentDocument.entities_count = Array.isArray(graph.entities) ? graph.entities.length : 0;
          this.currentDocument.edges_count = Array.isArray(graph.edges) ? graph.edges.length : 0;
        }
        this.isProcessing = false;
      },
      error: (error) => {
        this.errorMessage = 'Normalization failed: ' + error.message;
        this.isProcessing = false;
      }
    });
  }

  startIndexing() {
    if (!this.currentDocument?.graph_id) return;
    
    this.isProcessing = true;
    this.api.indexGraph(this.currentDocument.graph_id).subscribe({
      next: () => {
        if (this.currentDocument) {
          this.currentDocument.status = DocumentStatus.INDEXED;
        }
        this.isProcessing = false;
      },
      error: (error) => {
        this.errorMessage = 'Indexing failed: ' + error.message;
        this.isProcessing = false;
      }
    });
  }

  startRiskDetection() {
    if (!this.currentDocument?.graph_id) return;
    
    this.isProcessing = true;
    this.api.detectRisks(this.currentDocument.graph_id).subscribe({
      next: () => {
        if (this.currentDocument) {
          this.currentDocument.status = DocumentStatus.COMPLETED;
        }
        this.isProcessing = false;
      },
      error: (error) => {
        this.errorMessage = 'Risk detection failed: ' + error.message;
        this.isProcessing = false;
      }
    });
  }

  resetUpload() {
    this.currentDocument = undefined;
    this.errorMessage = undefined;
  }

  canExtract(): boolean {
    return this.currentDocument?.status === DocumentStatus.UPLOADED;
  }

  canNormalize(): boolean {
    return this.currentDocument?.status === DocumentStatus.EXTRACTED;
  }

  canIndex(): boolean {
    return this.currentDocument?.status === DocumentStatus.NORMALIZED;
  }

  canAnalyze(): boolean {
    return this.currentDocument?.status === DocumentStatus.INDEXED;
  }

  getStepClass(targetStatus: string): string {
    if (!this.currentDocument) {
      return 'h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600';
    }
    
    const statusOrder = ['uploaded', 'extracted', 'normalized', 'indexed', 'completed'];
    const currentIndex = statusOrder.indexOf(this.currentDocument.status);
    const targetIndex = statusOrder.indexOf(targetStatus);
    
    if (currentIndex >= targetIndex) {
      return 'h-8 w-8 rounded-full bg-green-500 flex items-center justify-center text-white';
    }
    return 'h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600';
  }

  getStatusClass(status: string): string {
    const baseClass = 'badge';
    if (status === 'completed') return `${baseClass} badge-low`;
    if (status === 'failed') return `${baseClass} badge-high`;
    return `${baseClass} bg-blue-100 text-blue-800`;
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  isPrimitive(value: unknown): boolean {
    return ['string', 'number', 'boolean'].includes(typeof value) || value === null || value === undefined;
  }
}

