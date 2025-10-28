import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-risks',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="card">
        <h2 class="text-2xl font-bold text-gray-900 mb-2">
          ⚠️ Risk Dashboard
        </h2>
        <p class="text-gray-600">
          Financial risks detected using hybrid AI reasoning and numeric rules.
        </p>
      </div>

      <!-- Risk Summary -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="card text-center">
          <div class="text-3xl font-bold text-gray-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Total Risks</div>
        </div>
        <div class="card text-center border-red-200">
          <div class="text-3xl font-bold text-red-600">0</div>
          <div class="text-sm text-gray-600 mt-1">High Severity</div>
        </div>
        <div class="card text-center border-yellow-200">
          <div class="text-3xl font-bold text-yellow-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Medium Severity</div>
        </div>
        <div class="card text-center border-green-200">
          <div class="text-3xl font-bold text-green-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Low Severity</div>
        </div>
      </div>

      <!-- Risk List -->
      <div class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          Detected Risks
        </h3>
        <div class="text-center py-12 text-gray-500">
          No risks detected yet. Upload and process a document to see risk analysis.
        </div>
      </div>

      <!-- Risk Categories -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="card">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">
            Interest Rate Risk
          </h3>
          <p class="text-sm text-gray-600">
            Variable-rate debt exposure and interest rate sensitivity analysis.
          </p>
        </div>
        <div class="card">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">
            Compliance Risk
          </h3>
          <p class="text-sm text-gray-600">
            Missing covenants, clauses, and regulatory compliance gaps.
          </p>
        </div>
        <div class="card">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">
            Liquidity Risk
          </h3>
          <p class="text-sm text-gray-600">
            Cash flow analysis and debt maturity schedules.
          </p>
        </div>
        <div class="card">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">
            Operational Risk
          </h3>
          <p class="text-sm text-gray-600">
            Invoice mismatches and reconciliation errors.
          </p>
        </div>
      </div>
    </div>
  `
})
export class RisksComponent {}

