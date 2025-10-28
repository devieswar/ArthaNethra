import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Document, DocumentStatus } from '../../models/document.model';
import { ApiService } from '../../services/api.service';

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
          Upload PDFs or ZIPs of financial documents (10-Ks, loan agreements, invoices) 
          for AI-powered extraction and analysis.
        </p>
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
              Supported formats: PDF, ZIP (max 100MB)
            </p>
            <input 
              type="file"
              #fileInput
              (change)="onFileSelected($event)"
              accept=".pdf,.zip"
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
export class UploadComponent {
  isDragging = false;
  isUploading = false;
  isProcessing = false;
  currentDocument?: Document;
  errorMessage?: string;

  constructor(private api: ApiService) {}

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
          this.currentDocument.graph_id = result.graph_id;
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
          this.currentDocument.graph_id = graph.id;
          this.currentDocument.entities_count = graph.entities.length;
          this.currentDocument.edges_count = graph.edges.length;
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
}

