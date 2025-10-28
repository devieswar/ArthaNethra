import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import Graph from 'graphology';
import Sigma from 'sigma';
import { Entity, EntityType } from '../../models/entity.model';
import { Risk, RiskSeverity } from '../../models/risk.model';
import { ApiService } from '../../services/api.service';

// Define proper types for graphology
type GraphNodeAttributes = {
  id: string;
  label: string;
  type: EntityType;
  size: number;
  color: string;
  x?: number;
  y?: number;
};

type GraphEdgeAttributes = {
  id: string;
  source: string;
  target: string;
  label?: string;
  type: string;
  color: string;
  size: number;
};

type FinancialGraph = any; // Using any for now due to graphology type issues

interface GraphNode {
  id: string;
  label: string;
  type: string;
  size: number;
  color: string;
  x?: number;
  y?: number;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type: string;
  color: string;
  size: number;
}

@Component({
  selector: 'app-graph',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-7xl mx-auto space-y-6">
      <!-- Page Header -->
      <div class="card">
        <h2 class="text-2xl font-bold text-gray-900 mb-2">
          🌐 Financial Knowledge Graph
        </h2>
        <p class="text-gray-600">
          Interactive visualization of financial entities and their relationships.
        </p>
      </div>

      <!-- Graph Controls -->
      <div class="card">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="flex items-center space-x-2">
            <label class="text-sm font-medium text-gray-700">Entity Type:</label>
            <select class="form-select" [(ngModel)]="selectedEntityType" (change)="applyFilters()">
              <option value="all">All Entities</option>
              <option value="company">Companies</option>
              <option value="subsidiary">Subsidiaries</option>
              <option value="instrument">Instruments</option>
              <option value="metric">Metrics</option>
            </select>
          </div>
          
          <div class="flex items-center space-x-2">
            <label class="text-sm font-medium text-gray-700">Risk Level:</label>
            <select class="form-select" [(ngModel)]="selectedRiskLevel" (change)="applyFilters()">
              <option value="all">All Levels</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
            </select>
          </div>

          <button class="btn-primary" (click)="refreshGraph()">
            🔄 Refresh Graph
          </button>
          
          <button class="btn-secondary" (click)="resetHighlight()">
            🎯 Reset Highlight
          </button>
        </div>
      </div>

      <!-- Graph Visualization -->
      <div class="card">
        <div class="h-96 bg-gray-50 rounded-lg relative">
          <div #graphContainer class="w-full h-full"></div>
          <div *ngIf="isLoading" class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
            <div class="text-center">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-2"></div>
              <p class="text-sm text-gray-600">Loading graph...</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Graph Stats -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="card">
          <div class="flex items-center">
            <div class="p-3 bg-blue-100 rounded-lg">
              <span class="text-2xl">🏢</span>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-500">Total Entities</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.totalEntities }}</p>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="flex items-center">
            <div class="p-3 bg-green-100 rounded-lg">
              <span class="text-2xl">🔗</span>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-500">Relationships</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.totalRelationships }}</p>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="flex items-center">
            <div class="p-3 bg-red-100 rounded-lg">
              <span class="text-2xl">⚠️</span>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-500">Risk Flags</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.riskFlags }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Selected Node Info -->
      <div *ngIf="selectedNode" class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Selected Entity</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-500">Name</p>
            <p class="font-medium">{{ selectedNode.label }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">Type</p>
            <p class="font-medium capitalize">{{ selectedNode.type }}</p>
          </div>
          <div *ngIf="selectedNodeRisk">
            <p class="text-sm text-gray-500">Risk Level</p>
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  [class]="getRiskBadgeClass(selectedNodeRisk.severity)">
              {{ selectedNodeRisk.severity | uppercase }}
            </span>
          </div>
          <div>
            <p class="text-sm text-gray-500">Connections</p>
            <p class="font-medium">{{ getNodeConnections(selectedNode.id) }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class GraphComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('graphContainer', { static: true }) graphContainer!: ElementRef;

  private graph!: FinancialGraph;
  private renderer!: Sigma;
  private entities: Entity[] = [];
  private risks: Risk[] = [];

  selectedEntityType = 'all';
  selectedRiskLevel = 'all';
  isLoading = false;
  selectedNode: GraphNode | null = null;
  selectedNodeRisk: Risk | null = null;

  stats = {
    totalEntities: 0,
    totalRelationships: 0,
    riskFlags: 0
  };

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadGraphData();
  }

  ngAfterViewInit() {
    this.initializeGraph();
  }

  ngOnDestroy() {
    if (this.renderer) {
      this.renderer.kill();
    }
  }

  private initializeGraph() {
    this.graph = new Graph();
    this.renderer = new Sigma(this.graph, this.graphContainer.nativeElement, {
      defaultNodeColor: '#666',
      defaultEdgeColor: '#999',
      labelSize: 12,
      labelWeight: 'bold',
      labelColor: { color: '#000' },
      zIndex: true
    });

    // Handle node clicks
    this.renderer.on('clickNode', (event) => {
      const nodeId = event.node;
      this.selectedNode = this.graph.getNodeAttributes(nodeId) as GraphNode;
      this.selectedNodeRisk = this.risks.find(r => r.affected_entity_ids.includes(nodeId)) || null;
    });

    // Handle background clicks
    this.renderer.on('clickStage', () => {
      this.selectedNode = null;
      this.selectedNodeRisk = null;
    });
  }

  private async loadGraphData() {
    this.isLoading = true;
    try {
      // Load entities and risks from API
      this.apiService.getEntities().subscribe(entities => {
        this.entities = entities;
        this.updateGraph();
        this.updateStats();
      });
      
      this.apiService.getRisks().subscribe(risks => {
        this.risks = risks;
        this.updateStats();
      });
    } catch (error) {
      console.error('Error loading graph data:', error);
      // Load sample data for demo
      this.loadSampleData();
    } finally {
      this.isLoading = false;
    }
  }

  private loadSampleData() {
    // Sample financial entities for demo
    this.entities = [
      {
        id: '1',
        name: 'ACME Corp',
        type: EntityType.COMPANY,
        properties: { sector: 'Technology', revenue: 1000000000 },
        citations: [],
        document_id: 'doc1',
        graph_id: 'graph1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: '2',
        name: 'ACME Subsidiary LLC',
        type: EntityType.SUBSIDIARY,
        properties: { parent: 'ACME Corp', location: 'Delaware' },
        citations: [],
        document_id: 'doc1',
        graph_id: 'graph1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: '3',
        name: 'Bank of America Loan',
        type: EntityType.INSTRUMENT,
        properties: { amount: 50000000, rate: 0.045, type: 'term_loan' },
        citations: [],
        document_id: 'doc1',
        graph_id: 'graph1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: '4',
        name: 'Debt-to-Equity Ratio',
        type: EntityType.METRIC,
        properties: { value: 0.65, period: 'Q4 2024' },
        citations: [],
        document_id: 'doc1',
        graph_id: 'graph1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];

    this.risks = [
      {
        id: '1',
        type: 'interest_rate_risk',
        severity: RiskSeverity.MEDIUM,
        description: 'Variable rate exposure above threshold',
        affected_entity_ids: ['3'],
        citations: [],
        score: 0.85,
        threshold: 0.8,
        actual_value: 0.85,
        recommendation: 'Consider hedging strategies',
        document_id: 'doc1',
        graph_id: 'graph1',
        detected_at: new Date().toISOString()
      }
    ];

    this.updateGraph();
    this.updateStats();
  }

  private updateGraph() {
    if (!this.graph) return;

    // Clear existing graph
    this.graph.clear();

    // Add nodes
    this.entities.forEach(entity => {
      if (this.shouldShowEntity(entity)) {
        this.graph.addNode(entity.id, {
          id: entity.id,
          label: entity.name,
          type: entity.type,
          size: this.getNodeSize(entity.type),
          color: this.getNodeColor(entity.type),
          x: Math.random() * 1000,
          y: Math.random() * 1000
        });
      }
    });

    // Add edges (relationships)
    this.addRelationships();

    // Refresh renderer
    this.renderer.refresh();
  }

  private addRelationships() {
    // Add sample relationships
    const relationships = [
      { source: '1', target: '2', type: 'owns', label: 'owns' },
      { source: '1', target: '3', type: 'has_loan', label: '$50M loan' },
      { source: '1', target: '4', type: 'has_metric', label: 'D/E ratio' },
      { source: '2', target: '3', type: 'guarantees', label: 'guarantees' }
    ];

    relationships.forEach((rel, index) => {
      if (this.graph.hasNode(rel.source) && this.graph.hasNode(rel.target)) {
        this.graph.addEdge(`edge-${index}`, rel.source, rel.target, {
          id: `edge-${index}`,
          source: rel.source,
          target: rel.target,
          label: rel.label,
          type: rel.type,
          color: this.getEdgeColor(rel.type),
          size: 2
        });
      }
    });
  }

  private shouldShowEntity(entity: Entity): boolean {
    if (this.selectedEntityType !== 'all' && entity.type !== this.selectedEntityType) {
      return false;
    }

    if (this.selectedRiskLevel !== 'all') {
      const entityRisk = this.risks.find(r => r.affected_entity_ids.includes(entity.id));
      if (!entityRisk || entityRisk.severity !== this.selectedRiskLevel) {
        return false;
      }
    }

    return true;
  }

  private getNodeSize(type: EntityType): number {
    const sizes: Record<EntityType, number> = {
      [EntityType.COMPANY]: 15,
      [EntityType.SUBSIDIARY]: 12,
      [EntityType.INSTRUMENT]: 10,
      [EntityType.METRIC]: 8,
      [EntityType.LOAN]: 10,
      [EntityType.INVOICE]: 8,
      [EntityType.CLAUSE]: 6,
      [EntityType.VENDOR]: 8,
      [EntityType.PERSON]: 8,
      [EntityType.LOCATION]: 6
    };
    return sizes[type] || 8;
  }

  private getNodeColor(type: EntityType): string {
    const colors: Record<EntityType, string> = {
      [EntityType.COMPANY]: '#3b82f6',
      [EntityType.SUBSIDIARY]: '#10b981',
      [EntityType.INSTRUMENT]: '#f59e0b',
      [EntityType.METRIC]: '#8b5cf6',
      [EntityType.LOAN]: '#f59e0b',
      [EntityType.INVOICE]: '#ef4444',
      [EntityType.CLAUSE]: '#6b7280',
      [EntityType.VENDOR]: '#8b5cf6',
      [EntityType.PERSON]: '#10b981',
      [EntityType.LOCATION]: '#6b7280'
    };
    return colors[type] || '#6b7280';
  }

  private getEdgeColor(type: string): string {
    const colors = {
      owns: '#3b82f6',
      has_loan: '#f59e0b',
      has_metric: '#8b5cf6',
      guarantees: '#ef4444'
    };
    return colors[type as keyof typeof colors] || '#6b7280';
  }

  private updateStats() {
    this.stats.totalEntities = this.entities.length;
    this.stats.totalRelationships = this.graph?.size || 0;
    this.stats.riskFlags = this.risks.length;
  }

  getNodeConnections(nodeId: string): number {
    return this.graph?.degree(nodeId) || 0;
  }

  getRiskBadgeClass(severity: RiskSeverity): string {
    const classes = {
      [RiskSeverity.HIGH]: 'bg-red-100 text-red-800',
      [RiskSeverity.MEDIUM]: 'bg-yellow-100 text-yellow-800',
      [RiskSeverity.LOW]: 'bg-green-100 text-green-800',
      [RiskSeverity.CRITICAL]: 'bg-red-200 text-red-900'
    };
    return classes[severity] || 'bg-gray-100 text-gray-800';
  }

  applyFilters() {
    this.updateGraph();
  }

  refreshGraph() {
    this.loadGraphData();
  }

  resetHighlight() {
    this.selectedNode = null;
    this.selectedNodeRisk = null;
    if (this.renderer) {
      this.renderer.setSetting('defaultNodeColor', '#666');
      this.renderer.refresh();
    }
  }

  highlightFromChat(entityIds: string[]) {
    if (!this.renderer) return;

    // Reset all nodes
    this.graph.forEachNode((nodeId: string) => {
      const nodeType = this.graph.getNodeAttribute(nodeId, 'type') as EntityType;
      this.graph.setNodeAttribute(nodeId, 'color', this.getNodeColor(nodeType));
    });

    // Highlight selected nodes
    entityIds.forEach(nodeId => {
      if (this.graph.hasNode(nodeId)) {
        this.graph.setNodeAttribute(nodeId, 'color', '#ff6b6b');
      }
    });

    this.renderer.refresh();
  }
}