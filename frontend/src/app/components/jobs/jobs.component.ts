import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';

interface ExtractJob {
  job_id: string;
  document_id: string;
  status: string;
  total?: number;
  completed?: number;
  failed?: number;
  result_path?: string;
}

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 mb-1">Extraction Jobs</h2>
            <p class="text-gray-600">History of recent ADE extractions.</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div *ngIf="isLoading" class="text-gray-600">Loading...</div>
        <div *ngIf="!isLoading && jobs.length === 0" class="text-gray-600">No jobs yet.</div>

        <div *ngIf="!isLoading && jobs.length > 0" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Job ID</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Progress</th>
                <th class="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr *ngFor="let j of jobs" (click)="select(j)" class="cursor-pointer hover:bg-gray-50">
                <td class="px-4 py-2 text-sm text-gray-900">{{ j.job_id }}</td>
                <td class="px-4 py-2 text-sm text-gray-700">{{ j.document_id }}</td>
                <td class="px-4 py-2 text-sm">
                  <span class="badge" [ngClass]="{
                    'bg-blue-100 text-blue-800': j.status==='processing',
                    'bg-green-100 text-green-800': j.status==='completed',
                    'bg-red-100 text-red-800': j.status==='failed'
                  }">{{ j.status }}</span>
                </td>
                <td class="px-4 py-2 text-sm text-gray-700">{{ j.completed || 0 }} / {{ j.total || '-' }}</td>
                <td class="px-4 py-2 text-right text-sm text-primary-700">Details</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div *ngIf="selected" class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-3">Job Details</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div><span class="text-gray-500">Job ID:</span> <span class="font-mono">{{ selected.job_id }}</span></div>
          <div><span class="text-gray-500">Document:</span> {{ selected.document_id }}</div>
          <div><span class="text-gray-500">Status:</span> {{ selected.status }}</div>
          <div><span class="text-gray-500">Progress:</span> {{ selected.completed || 0 }}/{{ selected.total || '-' }}</div>
          <div *ngIf="selected.result_path"><span class="text-gray-500">Stored:</span> {{ selected.result_path }}</div>
        </div>

        <div *ngIf="isLoadingResult" class="text-gray-600 mt-4">Loading result...</div>

        <div *ngIf="result && result.response" class="mt-4">
          <h4 class="font-medium text-gray-900 mb-2">Extracted Data</h4>
          <div class="space-y-4">
            <div>
              <h5 class="text-sm text-gray-700 mb-1">Key-Values</h5>
              <div class="overflow-x-auto border rounded" *ngIf="result.response.ade_output?.key_values?.length; else noKv">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr *ngFor="let kv of result.response.ade_output.key_values">
                      <td class="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">{{ kv.key }}</td>
                      <td class="px-3 py-2 text-sm text-gray-700"><pre class="whitespace-pre-wrap text-xs">{{ kv.value | json }}</pre></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <ng-template #noKv>
                <p class="text-sm text-gray-500">No key-values.</p>
              </ng-template>
            </div>

            <div>
              <h5 class="text-sm text-gray-700 mb-1">Entities ({{ result.response.ade_output?.entities?.length || 0 }})</h5>
              <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto">{{ result.response.ade_output?.entities | json }}</pre>
            </div>

            <div>
              <h5 class="text-sm text-gray-700 mb-1">Tables ({{ result.response.ade_output?.tables?.length || 0 }})</h5>
              <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto">{{ result.response.ade_output?.tables | json }}</pre>
            </div>
          </div>
        </div>
        <div *ngIf="result" class="mt-6">
          <div class="flex items-center justify-between mb-2">
            <h4 class="font-medium text-gray-900">Raw JSON</h4>
            <a [href]="getJobResultUrl(selected!)" target="_blank" class="btn btn-secondary btn-sm">Open JSON</a>
          </div>
          <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto max-h-96">{{ (result.response || result) | json }}</pre>
        </div>
      </div>
    </div>
  `
})

export class JobsComponent implements OnInit {
  jobs: ExtractJob[] = [];
  isLoading = false;
  selected?: ExtractJob;
  result: any;
  isLoadingResult = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load() {
    this.isLoading = true;
    this.api.getExtractJobs().subscribe({
      next: (rows) => { this.jobs = rows || []; this.isLoading = false; },
      error: () => { this.jobs = []; this.isLoading = false; }
    });
  }

  select(job: ExtractJob) {
    this.selected = job;
    this.result = undefined;
    this.isLoadingResult = true;
    this.api.getExtractJobResult(job.job_id).subscribe({
      next: (res) => { this.result = res; this.isLoadingResult = false; },
      error: () => { this.isLoadingResult = false; }
    });
  }

  getJobResultUrl(job: ExtractJob): string {
    return this.api.getExtractJobResultUrl(job.job_id);
  }
}


