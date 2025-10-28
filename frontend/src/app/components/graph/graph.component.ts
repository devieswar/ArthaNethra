import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-graph',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h2 class="text-2xl font-bold text-gray-900 mb-4">
        🌐 Knowledge Graph Visualization
      </h2>
      <p class="text-gray-600 mb-6">
        Interactive visualization of financial entities and their relationships using Sigma.js.
      </p>
      <div class="bg-gray-100 rounded-lg h-96 flex items-center justify-center">
        <p class="text-gray-500">Graph visualization will be rendered here using Sigma.js</p>
      </div>
      <div class="mt-4 flex space-x-4">
        <button class="btn btn-primary">Zoom In</button>
        <button class="btn btn-primary">Zoom Out</button>
        <button class="btn btn-secondary">Reset View</button>
        <select class="px-4 py-2 border border-gray-300 rounded-lg">
          <option>All Entity Types</option>
          <option>Companies</option>
          <option>Loans</option>
          <option>Subsidiaries</option>
        </select>
      </div>
    </div>
  `
})
export class GraphComponent {}

