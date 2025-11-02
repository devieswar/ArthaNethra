import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="space-y-6">
      <!-- Welcome Section -->
      <div class="card">
        <h2 class="text-3xl font-bold text-gray-900 mb-2">
          Welcome to ArthaNethra
        </h2>
        <p class="text-gray-600 mb-6">
          AI-powered financial investigation platform that transforms complex documents 
          into connected, explainable insights.
        </p>
        <div class="flex space-x-4">
          <button routerLink="/upload" class="btn btn-primary">
            📄 Upload Document
          </button>
          <button routerLink="/chat" class="btn btn-secondary">
            💬 Chat with AI
          </button>
        </div>
      </div>

      <!-- Features Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Feature 1 -->
        <div class="card hover:shadow-md transition-shadow cursor-pointer" routerLink="/upload">
          <div class="text-4xl mb-4">🗂️</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            Smart Document Ingestion
          </h3>
          <p class="text-sm text-gray-600">
            Upload financial PDFs and extract structured data with LandingAI ADE
          </p>
        </div>

        <!-- Feature 2 -->
        <div class="card hover:shadow-md transition-shadow cursor-pointer" routerLink="/graph">
          <div class="text-4xl mb-4">🌐</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            Knowledge Graph
          </h3>
          <p class="text-sm text-gray-600">
            Visualize relationships between entities, loans, and subsidiaries
          </p>
        </div>

        <!-- Feature 3 -->
        <div class="card hover:shadow-md transition-shadow cursor-pointer" routerLink="/risks">
          <div class="text-4xl mb-4">⚠️</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            Risk Detection
          </h3>
          <p class="text-sm text-gray-600">
            Detect financial risks using hybrid AI reasoning + numeric rules
          </p>
        </div>

        <!-- Feature 4: Documents -->
        <div class="card hover:shadow-md transition-shadow cursor-pointer" routerLink="/documents">
          <div class="text-4xl mb-4">📄</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            Documents
          </h3>
          <p class="text-sm text-gray-600">
            View uploaded and processed documents with statuses
          </p>
        </div>

        <!-- Feature 5 -->
        <div class="card hover:shadow-md transition-shadow cursor-pointer" routerLink="/chat">
          <div class="text-4xl mb-4">💬</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            AI Chatbot
          </h3>
          <p class="text-sm text-gray-600">
            Ask questions and get evidence-backed insights with citations
          </p>
        </div>

        <!-- Feature 6 -->
        <div class="card hover:shadow-md transition-shadow">
          <div class="text-4xl mb-4">📊</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            KPI Dashboards
          </h3>
          <p class="text-sm text-gray-600">
            Track profit/loss trends, debt ratios, and exposure distribution
          </p>
        </div>

        <!-- Feature 7 -->
        <div class="card hover:shadow-md transition-shadow">
          <div class="text-4xl mb-4">📑</div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            Evidence Viewer
          </h3>
          <p class="text-sm text-gray-600">
            View source PDFs with highlighted citations and jump to exact pages
          </p>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="card text-center">
          <div class="text-3xl font-bold text-primary-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Documents Processed</div>
        </div>
        <div class="card text-center">
          <div class="text-3xl font-bold text-accent-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Entities Extracted</div>
        </div>
        <div class="card text-center">
          <div class="text-3xl font-bold text-yellow-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Risks Detected</div>
        </div>
        <div class="card text-center">
          <div class="text-3xl font-bold text-blue-600">0</div>
          <div class="text-sm text-gray-600 mt-1">Queries Answered</div>
        </div>
      </div>

      <!-- Getting Started -->
      <div class="card bg-gradient-to-r from-primary-50 to-accent-50">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          🚀 Getting Started
        </h3>
        <ol class="space-y-2 text-sm text-gray-700">
          <li>1. Upload a financial document (10-K, loan agreement, invoice)</li>
          <li>2. Wait for ADE extraction to complete</li>
          <li>3. View the knowledge graph of entities and relationships</li>
          <li>4. Ask the AI chatbot questions about risks and compliance</li>
          <li>5. Review risk reports with clickable evidence</li>
        </ol>
      </div>
    </div>
  `,
  styles: []
})
export class DashboardComponent {}

