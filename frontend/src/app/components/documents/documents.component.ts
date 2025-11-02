import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Document } from '../../models/document.model';

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 mb-1">Documents</h2>
            <p class="text-gray-600">Uploaded and processed documents.</p>
          </div>
          <a routerLink="/upload" class="btn btn-primary">Upload New</a>
        </div>
      </div>

      <div class="card">
        <div *ngIf="isLoading" class="text-gray-600">Loading...</div>
        <div *ngIf="!isLoading && documents.length === 0" class="text-gray-600">No documents yet. Upload one to get started.</div>

        <div *ngIf="!isLoading && documents.length > 0" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Filename</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entities</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Edges</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pages</th>
                <th class="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr *ngFor="let d of documents">
                <td class="px-4 py-2 text-sm text-gray-900">{{ d.filename }}</td>
                <td class="px-4 py-2 text-sm">
                  <span class="badge bg-blue-100 text-blue-800">{{ d.status }}</span>
                </td>
                <td class="px-4 py-2 text-sm text-gray-700">{{ d.entities_count || 0 }}</td>
                <td class="px-4 py-2 text-sm text-gray-700">{{ d.edges_count || 0 }}</td>
                <td class="px-4 py-2 text-sm text-gray-700">{{ d.total_pages || '-' }}</td>
                <td class="px-4 py-2 text-right space-x-2">
                  <a 
                    routerLink="/upload" 
                    [queryParams]="{ document_id: d.id }" 
                    class="btn btn-secondary btn-sm">Continue</a>
                  <button 
                    (click)="delete(d.id)" 
                    class="btn btn-danger btn-sm">Delete</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `
})
export class DocumentsComponent implements OnInit {
  documents: Document[] = [];
  isLoading = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  private load() {
    this.isLoading = true;
    this.api.getDocuments().subscribe({
      next: (docs) => {
        this.documents = docs || [];
        this.isLoading = false;
      },
      error: () => {
        this.documents = [];
        this.isLoading = false;
      }
    });
  }

  delete(id: string) {
    if (!id) return;
    this.api.deleteDocument(id).subscribe({
      next: () => this.load(),
      error: () => this.load()
    });
  }
}


