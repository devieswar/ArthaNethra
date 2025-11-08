import { CommonModule } from '@angular/common';
import { Component, ElementRef, NgZone, OnDestroy, OnInit, Pipe, PipeTransform, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml, SafeResourceUrl } from '@angular/platform-browser';
import { EChartsOption } from 'echarts';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import circular from 'graphology-layout/circular';
import random from 'graphology-layout/random';
import MarkdownIt from 'markdown-it';
import { NgxEchartsModule } from 'ngx-echarts';
import { NgxExtendedPdfViewerModule } from 'ngx-extended-pdf-viewer';
import { firstValueFrom } from 'rxjs';
import Sigma from 'sigma';
import { ApiService } from '../../services/api.service';

@Pipe({
  name: 'sanitizeUrl',
  standalone: true
})
export class SafeUrlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  
  transform(url: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}

interface ChatSession {
  id: string;
  name: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
  message_count: number;
  isEditing?: boolean;  // For inline name editing
}

interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  graphData?: {
    entities: any[];
    relationships: any[];
  };
}

interface Document {
  id: string;
  filename: string;
  status: string;
  entities_count: number;
  edges_count: number;
  markdown_content?: string;
  graph_id?: string;
}

@Component({
  selector: 'app-chat-unified',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxExtendedPdfViewerModule, NgxEchartsModule],
  templateUrl: './chat-unified.component.html',
  styleUrls: ['./chat-unified.component.css']
})
export class ChatUnifiedComponent implements OnInit, OnDestroy {
  @ViewChild('chatMessages') chatMessages!: ElementRef;
  @ViewChild('sigmaContainer') sigmaContainer!: ElementRef;
  @ViewChild('sigmaContainerFullscreen') sigmaContainerFullscreen!: ElementRef;
  @ViewChild('responseGraphContainer') responseGraphContainer!: ElementRef;

  sessions: ChatSession[] = [];
  currentSession: ChatSession | null = null;
  messages: ChatMessage[] = [];
  userMessage = '';
  isLoading = false;
  isGraphFullscreen = false;
  isResponseGraphFullscreen = false;
  selectedMessageForGraph: ChatMessage | null = null;
  
  // Sigma graph
  private sigmaInstance: Sigma | null = null;
  private graphInstance: any = null;
  private responseSigmaInstance: Sigma | null = null;
  private responseGraphInstance: any = null;
  currentLayout: 'force' | 'circular' | 'grid' | 'random' = 'force'; // Default layout
  responseGraphLayout: 'force' | 'circular' | 'grid' | 'random' = 'circular'; // Layout for response graph
  layoutOptions: ('force' | 'circular' | 'grid' | 'random')[] = ['force', 'circular', 'grid', 'random'];
  
  allDocuments: Document[] = [];
  currentDocuments: Document[] = [];
  availableDocuments: Document[] = []; // Documents not yet in current session
  filteredAvailableDocuments: Document[] = []; // Filtered by search
  documentSearchQuery = '';
  
  showExplorer = false;
  showProgressModal = false;
  showAvailableDocuments = false; // Toggle to show available documents
  showDeleteConfirm = false; // Toggle delete confirmation dialog
  documentToDelete: Document | null = null;
  isDeleting = false;
  uploadingFile: File | null = null;
  
  // Explorer views
  explorerView: 'list' | 'graph' | 'entities' | 'markdown' | 'risks' | 'pdf' = 'list';
  selectedDocument: Document | null = null;
  graphEntities: any[] = [];
  graphEdges: any[] = [];
  documentRisks: any[] = [];
  riskSummary: any = null;
  riskChartOptions: EChartsOption = {};
  markdownHtml: SafeHtml | null = null;
  isMarkdownFullscreen = false;
  
  progressSteps: Array<{ name: string; label: string; status: 'pending' | 'active' | 'completed' | 'error' }> = [
    { name: 'upload', label: 'Uploading file...', status: 'pending' },
    { name: 'parsing', label: 'Parsing document...', status: 'pending' },
    { name: 'extracting', label: 'Extracting data...', status: 'pending' },
    { name: 'normalizing', label: 'Building knowledge graph...', status: 'pending' },
    { name: 'indexing', label: 'Indexing...', status: 'pending' }
  ];

  private markdownRenderer = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true
  });

  constructor(private api: ApiService, private sanitizer: DomSanitizer, private ngZone: NgZone) {
    // Customize markdown link renderer to handle citations
    const defaultRender = this.markdownRenderer.renderer.rules.link_open || 
      ((tokens: any, idx: any, options: any, env: any, self: any) => self.renderToken(tokens, idx, options));
    
    this.markdownRenderer.renderer.rules.link_open = (tokens: any, idx: any, options: any, env: any, self: any) => {
      const token = tokens[idx];
      const hrefIndex = token.attrIndex('href');
      
      if (hrefIndex >= 0) {
        const href = token.attrs![hrefIndex][1];
        
        // Check if this is a citation link (e.g., doc:doc_abc123 or document:doc_abc123)
        if (href.startsWith('doc:') || href.startsWith('document:')) {
          const docId = href.replace(/^(doc:|document:)/, '');
          token.attrSet('class', 'citation-link');
          token.attrSet('data-doc-id', docId);
          token.attrSet('href', 'javascript:void(0)');
          return self.renderToken(tokens, idx, options);
        }
      }
      
      return defaultRender(tokens, idx, options, env, self);
    };
  }

  async ngOnInit() {
    await this.loadSessions();
    await this.loadDocuments();
    
    // Create default session if none exist
    if (this.sessions.length === 0) {
      await this.createNewSession();
    }
    
    // Setup click handler for citation links
    this.setupCitationClickHandler();
  }
  
  private setupCitationClickHandler() {
    // Use event delegation to handle dynamically added citation links
    document.addEventListener('click', (event) => {
      const target = event.target as HTMLElement;
      const citationLink = target.closest('.citation-link');
      
      if (citationLink) {
        event.preventDefault();
        const docId = citationLink.getAttribute('data-doc-id');
        if (docId) {
          console.log('Citation clicked, doc ID:', docId);
          // Run inside Angular zone to trigger change detection
          this.ngZone.run(() => {
            this.openDocumentFromCitation(docId);
          });
        }
      }
    });
  }
  
  async openDocumentFromCitation(docId: string) {
    console.log('Available documents:', this.allDocuments.map(d => ({ id: d.id, filename: d.filename })));
    
    let document = this.allDocuments.find(doc => doc.id === docId);
    
    // If the document is missing locally, refresh document list once
    if (!document) {
      await this.loadDocuments();
      document = this.allDocuments.find(doc => doc.id === docId);
    }
    
    if (!document) {
      console.error('❌ Document not found after refresh. Looking for ID:', docId);
      console.error('Available document IDs:', this.allDocuments.map(d => d.id));
      return;
    }
    
    // If the document isn't yet attached to the active session, attach it automatically
    if (this.currentSession && !this.currentSession.document_ids.includes(document.id)) {
      console.log(`📎 Attaching document ${document.filename} to current session from citation click`);
      await this.addExistingDocument(document);
    }
    
    // Ensure explorer is visible and show the PDF
    this.showExplorer = true;
    this.viewDocumentPDF(document);
    
    console.log('✅ Opening document from citation:', document.filename);
  }

  ngOnDestroy() {
    // Clean up Sigma instance to prevent memory leaks
    if (this.sigmaInstance) {
      try {
        this.sigmaInstance.kill();
        this.sigmaInstance = null;
      } catch (err) {
        console.warn('Error cleaning up Sigma instance:', err);
      }
    }
  }

  async loadSessions() {
    try {
      this.sessions = await firstValueFrom(this.api.get('/chat/sessions'));
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  }

  async loadDocuments() {
    try {
      this.allDocuments = await firstValueFrom(this.api.getDocuments());
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  }

  async createNewSession() {
    try {
      const name = `Chat ${this.sessions.length + 1}`;
      const session = await firstValueFrom(this.api.post('/chat/sessions', { name }));
      this.sessions.push(session);
      await this.selectSession(session);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  }

  async selectSession(session: ChatSession) {
    this.currentSession = session;
    await this.loadMessages();
    this.updateCurrentDocuments();
    
    // Auto-open document explorer if this chat has documents or there are available documents to add
    if (
      (session.document_ids && session.document_ids.length > 0) ||
      this.availableDocuments.length > 0
    ) {
      this.showExplorer = true;
      // Reset to list view when switching sessions
      this.explorerView = 'list';
    } else {
      this.showExplorer = false;
    }
  }

  async loadMessages() {
    if (!this.currentSession) return;
    try {
      this.messages = await firstValueFrom(this.api.get(`/chat/sessions/${this.currentSession.id}/messages`));
      
      // Graph data now comes from backend, but fallback to extraction if not present
      this.messages.forEach(msg => {
        if (msg.role === 'assistant' && !msg.graphData) {
          this.extractGraphFromResponse(msg);
        }
      });
      
      setTimeout(() => this.scrollToBottom(), 100);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  }

  async deleteSession(sessionId: string, event: Event) {
    event.stopPropagation();
    if (!confirm('Delete this chat?')) return;
    
    try {
      await firstValueFrom(this.api.delete(`/chat/sessions/${sessionId}`));
      this.sessions = this.sessions.filter(s => s.id !== sessionId);
      if (this.currentSession?.id === sessionId) {
        this.currentSession = null;
        this.messages = [];
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  }

  async sendMessage() {
    if (!this.currentSession || !this.userMessage.trim() || this.isLoading) return;
    
    const message = this.userMessage.trim();
    this.userMessage = '';
    
    // Add user message to UI immediately
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: this.currentSession.id,
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    };
    this.messages.push(userMsg);
    setTimeout(() => this.scrollToBottom(), 100);
    
    this.isLoading = true;
    
    try {
      const response = await firstValueFrom(
        this.api.post(`/chat/sessions/${this.currentSession.id}/messages`, { message })
      );
      await this.loadMessages();
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async uploadDocument(event: any) {
    const file = event.target.files?.[0];
    if (!file || !this.currentSession) return;
    
    this.uploadingFile = file;
    this.showProgressModal = true;
    this.resetProgress();
    
    try {
      this.updateProgress('upload', 'active');
      let document = await firstValueFrom(this.api.uploadDocument(file));
      
      this.updateProgress('upload', 'completed');
      this.updateProgress('parsing', 'completed');
      this.updateProgress('extracting', 'active');
      
      await firstValueFrom(this.api.extractDocument(document.id));
      this.updateProgress('extracting', 'completed');
      this.updateProgress('normalizing', 'active');
      
      const normalizeResult = await firstValueFrom(this.api.normalizeDocument(document.id));
      const graph_id = normalizeResult?.graph_id;
      
      this.updateProgress('normalizing', 'completed');
      this.updateProgress('indexing', 'active');
      
      if (graph_id) {
        await firstValueFrom(this.api.indexGraph(graph_id));
      }
      this.updateProgress('indexing', 'completed');
      
      // Reload documents to get updated graph_id
      await this.loadDocuments();
      
      // Add document to session
      try {
        await firstValueFrom(
          this.api.post(`/chat/sessions/${this.currentSession.id}/documents/${document.id}`, {})
        );
      } catch (sessionError) {
        console.warn('Failed to add document to session (continuing anyway):', sessionError);
      }
      
      await this.loadSessions();
      this.updateCurrentDocuments();
      
      // Close modal immediately after completion
      setTimeout(() => {
        this.showProgressModal = false;
        this.uploadingFile = null;
        this.resetProgress();
      }, 500);
      
    } catch (error: any) {
      console.error('Upload failed:', error);
      const activeStep = this.progressSteps.find(s => s.status === 'active');
      if (activeStep) {
        activeStep.status = 'error';
      }
      
      // Close modal after 3 seconds even on error
      setTimeout(() => {
        this.showProgressModal = false;
        this.uploadingFile = null;
        this.resetProgress();
      }, 3000);
    }
    
    event.target.value = '';
  }

  async removeDocumentFromSession(docId: string) {
    if (!this.currentSession) return;
    try {
      await firstValueFrom(
        this.api.delete(`/chat/sessions/${this.currentSession.id}/documents/${docId}`)
      );
      
      // Update current session's document list
      if (this.currentSession.document_ids.includes(docId)) {
        this.currentSession.document_ids = this.currentSession.document_ids.filter(id => id !== docId);
      }
      
      // Reload all data
      await this.loadSessions();
      await this.loadDocuments();
      this.updateCurrentDocuments();
      
      console.log(`Removed document ${docId} from session`);
    } catch (error) {
      console.error('Failed to remove document from session:', error);
    }
  }

  updateCurrentDocuments() {
    if (!this.currentSession) {
      this.currentDocuments = [];
      this.availableDocuments = [];
      this.filteredAvailableDocuments = [];
      return;
    }
    this.currentDocuments = this.allDocuments.filter(
      doc => this.currentSession!.document_ids.includes(doc.id)
    );
    // Update available documents (not yet in session)
    const attachableStatuses: Array<Document['status']> = ['indexed'];
    this.availableDocuments = this.allDocuments.filter(
      doc => !this.currentSession!.document_ids.includes(doc.id) && attachableStatuses.includes(doc.status)
    );
    // Initialize filtered list
    this.filteredAvailableDocuments = [...this.availableDocuments];
  }

  filterAvailableDocuments() {
    if (!this.documentSearchQuery.trim()) {
      this.filteredAvailableDocuments = [...this.availableDocuments];
      return;
    }
    
    const query = this.documentSearchQuery.toLowerCase();
    this.filteredAvailableDocuments = this.availableDocuments.filter(doc =>
      doc.filename.toLowerCase().includes(query)
    );
  }

  async addExistingDocument(doc: Document) {
    if (!this.currentSession) return;
    
    try {
      await firstValueFrom(
        this.api.post(`/chat/sessions/${this.currentSession.id}/documents/${doc.id}`, {})
      );
      
      // Update session
      if (!this.currentSession.document_ids.includes(doc.id)) {
        this.currentSession.document_ids.push(doc.id);
      }
      
      this.updateCurrentDocuments();
      this.showAvailableDocuments = false; // Close modal
      console.log(`Added document ${doc.filename} to session`);
    } catch (error) {
      console.error('Failed to add existing document to session:', error);
    }
  }

  async viewDocumentGraph(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'graph';
    
    // Reset graph data
    this.graphEntities = [];
    this.graphEdges = [];
    
    // Destroy existing Sigma instance
    if (this.sigmaInstance) {
      try {
        this.sigmaInstance.kill();
        this.sigmaInstance = null;
      } catch (err) {
        console.warn('Error destroying Sigma instance:', err);
      }
    }
    
    if (!doc.graph_id) {
      console.warn('No graph_id for document:', doc.id);
      return;
    }
    
    try {
      // Load entities for graph
      const entities = await firstValueFrom(this.api.get(`/entities/graph/${doc.graph_id}`));
      this.graphEntities = entities || [];
      
      // Load edges/relationships for this specific graph
      try {
        const relationships = await firstValueFrom(this.api.get(`/relationships/graph/${doc.graph_id}`));
        this.graphEdges = relationships || [];
        console.log('🔗 Raw relationships from API:', this.graphEdges.slice(0, 3));
      } catch (err) {
        console.warn('No relationships loaded:', err);
        this.graphEdges = [];
      }
      
      console.log(`📊 Loaded ${this.graphEntities.length} entities and ${this.graphEdges.length} relationships for graph ${doc.graph_id}`);
      
      // Render graph with Sigma after DOM updates
      setTimeout(() => this.renderSigmaGraph(false), 150);
    } catch (error) {
      console.error('Failed to load graph entities:', error);
      this.graphEntities = [];
      this.graphEdges = [];
    }
  }

  // Apply layout to graph
  private applyLayout(graph: any, layout: 'force' | 'circular' | 'grid' | 'random'): void {
    console.log(`📐 Applying ${layout} layout...`);
    
    switch (layout) {
      case 'force':
        // Apply ForceAtlas2 for physics-based layout
        random.assign(graph, { scale: 100 }); // Start with random positions
        forceAtlas2.assign(graph, {
          iterations: 100,
          settings: {
            gravity: 1,
            scalingRatio: 10,
            strongGravityMode: false,
            slowDown: 1,
            barnesHutOptimize: graph.order > 100,
            barnesHutTheta: 0.5
          }
        });
        break;
      
      case 'circular':
        // Apply circular layout
        circular.assign(graph, { scale: 100 });
        break;
      
      case 'grid':
        // Apply grid layout
        const nodes = graph.nodes();
        const gridSize = Math.ceil(Math.sqrt(nodes.length));
        const spacing = 200 / gridSize;
        
        nodes.forEach((node: string, index: number) => {
          const row = Math.floor(index / gridSize);
          const col = index % gridSize;
          graph.setNodeAttribute(node, 'x', (col - gridSize / 2) * spacing);
          graph.setNodeAttribute(node, 'y', (row - gridSize / 2) * spacing);
        });
        break;
      
      case 'random':
        // Apply random layout
        random.assign(graph, { scale: 100 });
        break;
    }
    
    console.log(`✅ ${layout} layout applied`);
  }

  // Change layout for document explorer graph
  changeLayout(layout: 'force' | 'circular' | 'grid' | 'random'): void {
    this.currentLayout = layout;
    if (this.graphInstance && this.sigmaInstance) {
      this.applyLayout(this.graphInstance, layout);
      this.sigmaInstance.refresh();
    }
  }

  // Change layout for response graph
  changeResponseGraphLayout(layout: 'force' | 'circular' | 'grid' | 'random'): void {
    this.responseGraphLayout = layout;
    if (this.responseGraphInstance && this.responseSigmaInstance) {
      this.applyLayout(this.responseGraphInstance, layout);
      this.responseSigmaInstance.refresh();
    }
  }
  
  openGraphFullscreen() {
    this.isGraphFullscreen = true;
    setTimeout(() => this.renderSigmaGraph(true), 0);
  }
  
  closeGraphFullscreen() {
    this.isGraphFullscreen = false;
    setTimeout(() => this.renderSigmaGraph(false), 0);
  }
  
  private renderSigmaGraph(fullscreen: boolean = false) {
    console.log(`🎨 renderSigmaGraph called (fullscreen: ${fullscreen})`);
    console.log(`   Entities to render: ${this.graphEntities.length}`);
    console.log(`   Edges to render: ${this.graphEdges.length}`);
    
    // Select the appropriate container
    const container = fullscreen ? this.sigmaContainerFullscreen : this.sigmaContainer;
    
    // Check if container is available in DOM
    if (!container || !container.nativeElement) {
      console.warn(`❌ Sigma container not available in DOM yet (fullscreen: ${fullscreen})`);
      return;
    }
    
    if (this.graphEntities.length === 0) {
      console.warn('❌ No entities to render');
      return;
    }
    
    console.log('✅ Container and entities ready');
    
    try {
      // Destroy existing instance
      if (this.sigmaInstance) {
        console.log('🗑️ Destroying existing Sigma instance');
        this.sigmaInstance.kill();
        this.sigmaInstance = null;
      }
      
      // Create new graph
      console.log('📦 Creating new Graphology instance');
      this.graphInstance = new Graph();
      
      // Color mapping for entity types
      const typeColors: { [key: string]: string } = {
        'Company': '#3b82f6',
        'Location': '#10b981',
        'Person': '#f59e0b',
        'Loan': '#ef4444',
        'Metric': '#8b5cf6',
        'Clause': '#ec4899',
        'Date': '#14b8a6',
        'Invoice': '#f97316',
        'Contract': '#6366f1'
      };
      
      // Add nodes (positions will be set by layout algorithm)
      console.log('🔵 Adding nodes to graph...');
      this.graphEntities.forEach((entity) => {
        (this.graphInstance as any).addNode(entity.id, {
          label: entity.name,
          x: 0,
          y: 0,
          size: 8,
          color: typeColors[entity.type] || '#94a3b8'
        });
      });
      console.log(`✅ Added ${this.graphEntities.length} nodes`);
      
      // Add edges
      console.log('🔗 Adding edges to graph...');
      console.log(`   Total edges to process: ${this.graphEdges.length}`);
      if (this.graphEdges.length > 0) {
        console.log('   Sample edge:', this.graphEdges[0]);
      }
      
      let edgesAdded = 0;
      let edgesSkipped = 0;
      this.graphEdges.forEach((edge, index) => {
        try {
          const hasSource = (this.graphInstance as any).hasNode(edge.from_entity_id);
          const hasTarget = (this.graphInstance as any).hasNode(edge.to_entity_id);
          
          if (hasSource && hasTarget) {
            // Use unique edge ID
            const edgeId = `edge_${index}`;
            (this.graphInstance as any).addEdgeWithKey(
              edgeId,
              edge.from_entity_id, 
              edge.to_entity_id, 
              {
                label: edge.relationship_type || 'RELATED_TO',
                size: 2,  // Thinner edges
                color: '#ef4444',  // Bright red
                type: 'arrow'
              }
            );
            edgesAdded++;
            if (index < 3) {
              console.log(`   ✅ Edge ${index}: ${edge.from_entity_id} -> ${edge.to_entity_id} (${edge.relationship_type})`);
            }
          } else {
            edgesSkipped++;
            if (edgesSkipped <= 3) {
              console.warn(`   ❌ Missing nodes for edge ${index}: ${edge.from_entity_id} -> ${edge.to_entity_id} (source:${hasSource}, target:${hasTarget})`);
            }
          }
        } catch (err) {
          console.error(`   ❌ Failed to add edge ${edge.from_entity_id} -> ${edge.to_entity_id}:`, err);
        }
      });
      
      console.log(`✅ Added ${edgesAdded} edges (skipped ${edgesSkipped}) out of ${this.graphEdges.length} total`);
      
      // Apply layout to the graph
      this.applyLayout(this.graphInstance, this.currentLayout);
      
      // Create Sigma instance with edge rendering enabled
      console.log('🎨 Creating Sigma instance with settings...');
      const sigmaSettings = {
        // Node rendering
        renderLabels: true,
        labelSize: 10,
        labelWeight: 'normal',
        labelColor: { color: '#1f2937' },
        defaultNodeColor: '#10b981',
        minNodeSize: 5,
        maxNodeSize: 15,
        
        // Edge rendering - CRITICAL for visibility
        renderEdgeLabels: true,  // ✅ Show relationship types on edges
        edgeLabelSize: 10,
        edgeLabelColor: { color: '#6b7280' },  // Gray text
        edgeLabelWeight: 'normal',
        defaultEdgeColor: '#ef4444',  // Bright red
        defaultEdgeType: 'arrow',
        minEdgeSize: 1,
        maxEdgeSize: 4,
        
        // Force edge rendering
        hideEdgesOnMove: false,
        hideLabelsOnMove: false,
        
        // Enable interactions
        enableEdgeHoverEvents: true,
        enableEdgeClickEvents: true,
        enableEdgeEvents: true
      };
      console.log('   Sigma settings:', sigmaSettings);
      
      this.sigmaInstance = new Sigma(
        this.graphInstance,
        container.nativeElement,
        sigmaSettings
      );
      
      console.log('🎨 Sigma instance created, enabling node dragging...');
      
      // Enable node dragging
      let draggedNode: string | null = null;
      let isDragging = false;
      
      // Mouse down on node - start drag
      this.sigmaInstance.on('downNode', (e: any) => {
        isDragging = true;
        draggedNode = e.node;
        (this.graphInstance as any).setNodeAttribute(draggedNode, 'highlighted', true);
        container.nativeElement.style.cursor = 'grabbing';
      });
      
      // Hover on node - show grab cursor
      this.sigmaInstance.on('enterNode', () => {
        container.nativeElement.style.cursor = 'grab';
      });
      
      // Leave node - reset cursor
      this.sigmaInstance.on('leaveNode', () => {
        if (!isDragging) {
          container.nativeElement.style.cursor = 'default';
        }
      });
      
      // Edge hover - show relationship details in tooltip
      this.sigmaInstance.on('enterEdge', (event: any) => {
        const edgeId = event.edge;
        const edge = this.graphEdges.find((e: any) => `edge_${this.graphEdges.indexOf(e)}` === edgeId);
        
        if (edge && edge.properties) {
          const reasoning = edge.properties.reasoning || 'No reasoning provided';
          const confidence = edge.properties.confidence ? ` (confidence: ${(edge.properties.confidence * 100).toFixed(0)}%)` : '';
          const detectedBy = edge.properties.detected_by || 'unknown';
          
          // Create or update tooltip
          let tooltip = document.getElementById('edge-tooltip');
          if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'edge-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = 'rgba(31, 41, 55, 0.95)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '12px';
            tooltip.style.maxWidth = '300px';
            tooltip.style.zIndex = '10000';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
            document.body.appendChild(tooltip);
          }
          
          tooltip.innerHTML = `
            <div style="margin-bottom: 4px"><strong>${edge.relationship_type || 'RELATIONSHIP'}</strong></div>
            <div style="color: #d1d5db; font-size: 11px">${reasoning}${confidence}</div>
            <div style="color: #9ca3af; font-size: 10px; margin-top: 4px">Detected by: ${detectedBy}</div>
          `;
          tooltip.style.display = 'block';
          
          // Position tooltip near mouse
          const updateTooltipPosition = (e: MouseEvent) => {
            if (tooltip) {
              tooltip.style.left = (e.clientX + 15) + 'px';
              tooltip.style.top = (e.clientY + 15) + 'px';
            }
          };
          
          container.nativeElement.addEventListener('mousemove', updateTooltipPosition);
          (tooltip as any)._removeListener = () => {
            container.nativeElement.removeEventListener('mousemove', updateTooltipPosition);
          };
        }
      });
      
      // Leave edge - hide tooltip
      this.sigmaInstance.on('leaveEdge', () => {
        const tooltip = document.getElementById('edge-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });
      
      // Click on edge - show detailed information
      this.sigmaInstance.on('clickEdge', (event: any) => {
        const edgeId = event.edge;
        const edge = this.graphEdges.find((e: any) => `edge_${this.graphEdges.indexOf(e)}` === edgeId);
        
        if (edge) {
          console.group('🔗 Relationship Details');
          console.log('Type:', edge.relationship_type || 'RELATIONSHIP');
          console.log('From:', edge.from_entity_id);
          console.log('To:', edge.to_entity_id);
          console.log('Properties:', edge.properties);
          if (edge.properties?.reasoning) {
            console.log('Reasoning:', edge.properties.reasoning);
          }
          if (edge.properties?.confidence) {
            console.log('Confidence:', (edge.properties.confidence * 100).toFixed(1) + '%');
          }
          if (edge.properties?.detected_by) {
            console.log('Detected by:', edge.properties.detected_by);
          }
          console.groupEnd();
          
          // Optionally highlight the edge
          (this.graphInstance as any).setEdgeAttribute(edgeId, 'color', '#3b82f6'); // Blue highlight
          setTimeout(() => {
            (this.graphInstance as any).setEdgeAttribute(edgeId, 'color', '#ef4444'); // Back to red
          }, 2000);
        }
      });
      
      // Mouse move - update node position
      this.sigmaInstance.getMouseCaptor().on('mousemovebody', (e: any) => {
        if (!isDragging || !draggedNode || !this.sigmaInstance) return;
        
        // Get new position from mouse
        const pos = this.sigmaInstance.viewportToGraph(e);
        
        // Update node position
        (this.graphInstance as any).setNodeAttribute(draggedNode, 'x', pos.x);
        (this.graphInstance as any).setNodeAttribute(draggedNode, 'y', pos.y);
        
        // Prevent camera movement while dragging
        e.preventSigmaDefault();
        e.original.preventDefault();
        e.original.stopPropagation();
      });
      
      // Mouse up - end drag
      this.sigmaInstance.getMouseCaptor().on('mouseup', () => {
        if (draggedNode) {
          (this.graphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.nativeElement.style.cursor = 'default';
      });
      
      // Mouse leave container - end drag
      this.sigmaInstance.getMouseCaptor().on('mouseleave', () => {
        if (draggedNode) {
          (this.graphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.nativeElement.style.cursor = 'default';
      });
      
      this.sigmaInstance.refresh();
      console.log('✅ Node dragging enabled');
      
      // Verify graph structure
      const nodeCount = (this.graphInstance as any).order;
      const edgeCount = (this.graphInstance as any).size;
      console.log('📊 Final Graphology stats:');
      console.log(`   Nodes in graph: ${nodeCount}`);
      console.log(`   Edges in graph: ${edgeCount}`);
      
      // Log edge details
      const edgeIds = (this.graphInstance as any).edges();
      console.log(`   Total edge IDs in graph: ${edgeIds.length}`);
      if (edgeIds.length > 0) {
        const firstEdge = (this.graphInstance as any).getEdgeAttributes(edgeIds[0]);
        console.log('   Sample edge attributes:', firstEdge);
      }
      
      console.log(`✅ Sigma graph rendered: ${this.graphEntities.length} nodes, ${edgesAdded} edges`);
    } catch (error) {
      console.error('Failed to render Sigma graph:', error);
    }
  }

  async viewDocumentMarkdown(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'markdown';
    this.markdownHtml = null;
    
    try {
      // Fetch document details which should include markdown_content
      const docDetails = await firstValueFrom(this.api.get(`/documents/${doc.id}`));
      const markdownContent = docDetails?.markdown_content || doc.markdown_content;
      if (markdownContent) {
        this.selectedDocument = { ...doc, markdown_content: markdownContent };
        this.markdownHtml = this.renderMarkdown(markdownContent);
      }
    } catch (error) {
      console.error('Failed to load markdown:', error);
    }
  }

  async viewDocumentEntities(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'entities';
    this.graphEntities = [];
    
    if (!doc.graph_id) {
      console.warn('No graph_id for document:', doc.id);
      return;
    }
    
    try {
      const entities = await firstValueFrom(this.api.get(`/entities/graph/${doc.graph_id}`));
      this.graphEntities = entities || [];
      console.log(`Loaded ${this.graphEntities.length} entities for graph ${doc.graph_id}`);
    } catch (error) {
      console.error('Failed to load entities:', error);
      this.graphEntities = [];
    }
  }

  async viewDocumentRisks(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'risks';
    this.documentRisks = [];
    this.riskSummary = null;
    this.riskChartOptions = {};
    
    try {
      // Load risks for document
      const response = await firstValueFrom(
        this.api.get(`/risks/document/${doc.id}`)
      );
      this.documentRisks = response.risks || [];
      this.riskSummary = response.summary || null;
      console.log(`Loaded ${this.documentRisks.length} risks for document ${doc.id}`);
      
      // Generate risk chart
      if (this.riskSummary && (this.riskSummary.total_risks || 0) > 0) {
        this.riskChartOptions = {
          tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
          },
          legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: { fontSize: 11 }
          },
          series: [
            {
              name: 'Risk Severity',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
              },
              label: {
                show: false,
                position: 'center'
              },
              emphasis: {
                label: {
                  show: true,
                  fontSize: 16,
                  fontWeight: 'bold'
                }
              },
              labelLine: {
                show: false
              },
              data: [
                { value: this.riskSummary.critical_severity || 0, name: 'Critical', itemStyle: { color: '#dc2626' } },
                { value: this.riskSummary.high_severity || 0, name: 'High', itemStyle: { color: '#ea580c' } },
                { value: this.riskSummary.medium_severity || 0, name: 'Medium', itemStyle: { color: '#f59e0b' } },
                { value: this.riskSummary.low_severity || 0, name: 'Low', itemStyle: { color: '#10b981' } }
              ]
            }
          ]
        };
      }
    } catch (error) {
      console.error('Failed to load risks:', error);
      this.documentRisks = [];
      this.riskSummary = null;
    }
  }

  async viewDocumentPDF(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'pdf';
  }

  resetProgress() {
    this.progressSteps.forEach(step => step.status = 'pending');
  }

  updateProgress(name: string, status: 'pending' | 'active' | 'completed' | 'error') {
    const step = this.progressSteps.find(s => s.name === name);
    if (step) step.status = status;
  }

  getProgress(): number {
    const completed = this.progressSteps.filter(s => s.status === 'completed').length;
    return Math.round((completed / this.progressSteps.length) * 100);
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }

  scrollToBottom() {
    if (this.chatMessages) {
      this.chatMessages.nativeElement.scrollTop = this.chatMessages.nativeElement.scrollHeight;
    }
  }

  // Helper method for iterating over object keys in template
  objectKeys(obj: any): string[] {
    return obj ? Object.keys(obj) : [];
  }

  private formatNumber(value: number | string): string {
    if (value === null || value === undefined) {
      return '';
    }
    let num = Number(value);
    const suffixes = ['', 'K', 'M', 'B', 'T'];
    let suffixIndex = 0;
    while (num >= 1000 && suffixIndex < suffixes.length - 1) {
      num /= 1000;
      suffixIndex++;
    }
    const formatted = num.toFixed(2) + suffixes[suffixIndex];
    return formatted;
  }

  openMarkdownFullscreen() {
    this.isMarkdownFullscreen = true;
  }

  closeMarkdownFullscreen() {
    this.isMarkdownFullscreen = false;
  }

  // Chat name editing methods
  private originalSessionName = '';

  startEditSessionName(session: ChatSession, event: Event) {
    event.stopPropagation();
    this.originalSessionName = session.name;
    session.isEditing = true;
    
    // Focus the input after Angular renders it
    setTimeout(() => {
      const input = document.querySelector(`input[aria-label="Edit chat name"]`) as HTMLInputElement;
      if (input) {
        input.focus();
        input.select();
      }
    }, 50);
  }

  async saveSessionName(session: ChatSession) {
    if (!session.isEditing) return;
    
    const newName = session.name.trim();
    if (!newName) {
      session.name = this.originalSessionName;
      session.isEditing = false;
      return;
    }
    
    if (newName === this.originalSessionName) {
      session.isEditing = false;
      return;
    }
    
    try {
      // Update on backend - send name in request body
      await firstValueFrom(
        this.api.put(`/chat/sessions/${session.id}`, { name: newName })
      );
      console.log(`Session name updated to: ${newName}`);
      session.isEditing = false;
    } catch (error) {
      console.error('Failed to update session name:', error);
      session.name = this.originalSessionName;
      session.isEditing = false;
    }
  }

  cancelEditSessionName(session: ChatSession) {
    session.name = this.originalSessionName;
    session.isEditing = false;
  }

  // Make renderMarkdown public for template access
  renderMarkdown(content: string): SafeHtml {
    const html = this.markdownRenderer.render(content || '');
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  // Extract entities and relationships from AI response text
  extractGraphFromResponse(message: ChatMessage): void {
    if (message.role !== 'assistant' || !message.content) {
      return;
    }

    const entities: any[] = [];
    const relationships: any[] = [];
    const entityMap = new Map<string, any>();
    let entityIdCounter = 0;

    // Simple pattern matching for common entity mentions
    // Looking for: "Company Name", dollar amounts, locations, dates, etc.
    
    // Extract company/organization names (capitalized words or phrases in quotes)
    const companyPattern = /(?:"([^"]+)"|([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+))/g;
    let match;
    
    while ((match = companyPattern.exec(message.content)) !== null) {
      const name = match[1] || match[2];
      if (name && !entityMap.has(name)) {
        const entityId = `entity_${entityIdCounter++}`;
        entityMap.set(name, {
          id: entityId,
          name: name,
          type: 'Organization',
          properties: {}
        });
        entities.push(entityMap.get(name));
      }
    }

    // Extract monetary amounts
    const moneyPattern = /\$\s*([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand)?/gi;
    while ((match = moneyPattern.exec(message.content)) !== null) {
      const amount = match[1];
      const scale = match[2] || '';
      const name = `$${amount}${scale ? ' ' + scale : ''}`;
      if (!entityMap.has(name)) {
        const entityId = `entity_${entityIdCounter++}`;
        entityMap.set(name, {
          id: entityId,
          name: name,
          type: 'Money',
          properties: { amount: match[1], scale: scale }
        });
        entities.push(entityMap.get(name));
      }
    }

    // Extract dates
    const datePattern = /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|Q[1-4]\s+\d{4}|\d{4}/g;
    while ((match = datePattern.exec(message.content)) !== null) {
      const date = match[0];
      if (!entityMap.has(date)) {
        const entityId = `entity_${entityIdCounter++}`;
        entityMap.set(date, {
          id: entityId,
          name: date,
          type: 'Date',
          properties: {}
        });
        entities.push(entityMap.get(date));
      }
    }

    // Extract relationships from common phrases
    const relationshipPatterns = [
      { pattern: /(\w+(?:\s+\w+)*)\s+(?:acquired|purchased)\s+(\w+(?:\s+\w+)*)/gi, type: 'ACQUIRED' },
      { pattern: /(\w+(?:\s+\w+)*)\s+(?:invested in|invested)\s+(\w+(?:\s+\w+)*)/gi, type: 'INVESTED_IN' },
      { pattern: /(\w+(?:\s+\w+)*)\s+(?:reported|announced)\s+(\$[\d,]+(?:\.\d{2})?(?:\s+(?:million|billion))?)/gi, type: 'REPORTED' },
      { pattern: /(\w+(?:\s+\w+)*)\s+(?:revenue|earnings)\s+(?:of|was)\s+(\$[\d,]+(?:\.\d{2})?(?:\s+(?:million|billion))?)/gi, type: 'HAS_REVENUE' }
    ];

    relationshipPatterns.forEach(({ pattern, type }) => {
      const regex = new RegExp(pattern);
      while ((match = regex.exec(message.content)) !== null) {
        const source = match[1];
        const target = match[2];
        
        const sourceEntity = entityMap.get(source);
        const targetEntity = entityMap.get(target);
        
        if (sourceEntity && targetEntity) {
          relationships.push({
            id: `rel_${relationships.length}`,
            from_entity_id: sourceEntity.id,
            to_entity_id: targetEntity.id,
            relationship_type: type,
            properties: {}
          });
        }
      }
    });

    // Store the extracted graph data
    message.graphData = {
      entities: entities,
      relationships: relationships
    };

    console.log('Extracted graph from response:', {
      entities: entities.length,
      relationships: relationships.length
    });
  }

  // Check if message has graph data to display
  hasGraphData(message: ChatMessage): boolean {
    return message.role === 'assistant' && 
           message.graphData !== undefined && 
           message.graphData.entities.length > 0;
  }

  // Open response graph in fullscreen modal
  openResponseGraph(message: ChatMessage): void {
    if (!this.hasGraphData(message)) {
      // Try to extract graph if not already done
      this.extractGraphFromResponse(message);
      if (!this.hasGraphData(message)) {
        console.warn('No graph data available for this message');
        return;
      }
    }

    this.selectedMessageForGraph = message;
    this.isResponseGraphFullscreen = true;
    
    // Render graph after DOM updates
    setTimeout(() => this.renderResponseGraph(), 150);
  }

  // Close response graph modal
  closeResponseGraph(): void {
    this.isResponseGraphFullscreen = false;
    this.selectedMessageForGraph = null;
    
    // Clean up Sigma instance
    if (this.responseSigmaInstance) {
      try {
        this.responseSigmaInstance.kill();
        this.responseSigmaInstance = null;
      } catch (err) {
        console.warn('Error cleaning up response Sigma instance:', err);
      }
    }
  }

  // Render the response graph using Sigma.js
  private renderResponseGraph(): void {
    if (!this.selectedMessageForGraph?.graphData || !this.responseGraphContainer) {
      console.warn('Cannot render response graph: missing data or container');
      return;
    }

    const { entities, relationships } = this.selectedMessageForGraph.graphData;

    console.log('Rendering response graph:', {
      entities: entities.length,
      relationships: relationships.length
    });

    try {
      // Clean up existing instance
      if (this.responseSigmaInstance) {
        this.responseSigmaInstance.kill();
        this.responseSigmaInstance = null;
      }

      // Create new graph
      this.responseGraphInstance = new Graph();

      // Color mapping for entity types
      const typeColors: { [key: string]: string } = {
        'Organization': '#3b82f6',
        'Company': '#3b82f6',
        'Money': '#10b981',
        'Date': '#f59e0b',
        'Person': '#ec4899',
        'Location': '#8b5cf6'
      };

      // Add nodes (positions will be set by layout algorithm)
      entities.forEach((entity) => {
        (this.responseGraphInstance as any).addNode(entity.id, {
          label: entity.name,
          x: 0,
          y: 0,
          size: 10,
          color: typeColors[entity.type] || '#94a3b8'
        });
      });

      // Add edges
      relationships.forEach((rel, index) => {
        const hasSource = (this.responseGraphInstance as any).hasNode(rel.from_entity_id);
        const hasTarget = (this.responseGraphInstance as any).hasNode(rel.to_entity_id);

        if (hasSource && hasTarget) {
          (this.responseGraphInstance as any).addEdgeWithKey(
            `edge_${index}`,
            rel.from_entity_id,
            rel.to_entity_id,
            {
              label: rel.relationship_type || 'RELATED_TO',
              size: 2,
              color: '#ef4444',
              type: 'arrow'
            }
          );
        }
      });

      // Apply layout to the response graph
      this.applyLayout(this.responseGraphInstance, this.responseGraphLayout);

      // Create Sigma instance
      this.responseSigmaInstance = new Sigma(
        this.responseGraphInstance,
        this.responseGraphContainer.nativeElement,
        {
          renderLabels: true,
          renderEdgeLabels: true
        } as any
      );

      console.log('Response graph rendered successfully');

      // Enable node dragging
      const container = this.responseGraphContainer.nativeElement;
      let draggedNode: string | null = null;
      let isDragging = false;

      // Mouse down on node - start drag
      this.responseSigmaInstance.on('downNode', (e: any) => {
        isDragging = true;
        draggedNode = e.node;
        (this.responseGraphInstance as any).setNodeAttribute(draggedNode, 'highlighted', true);
        container.style.cursor = 'grabbing';
      });

      // Hover on node - show grab cursor
      this.responseSigmaInstance.on('enterNode', () => {
        container.style.cursor = 'grab';
      });

      // Leave node - reset cursor
      this.responseSigmaInstance.on('leaveNode', () => {
        if (!isDragging) {
          container.style.cursor = 'default';
        }
      });

      // Mouse move - update node position
      this.responseSigmaInstance.getMouseCaptor().on('mousemovebody', (e: any) => {
        if (!isDragging || !draggedNode || !this.responseSigmaInstance) return;

        // Get new position from mouse
        const pos = this.responseSigmaInstance.viewportToGraph(e);

        // Update node position
        (this.responseGraphInstance as any).setNodeAttribute(draggedNode, 'x', pos.x);
        (this.responseGraphInstance as any).setNodeAttribute(draggedNode, 'y', pos.y);

        // Prevent camera movement while dragging
        e.preventSigmaDefault();
        e.original.preventDefault();
        e.original.stopPropagation();
      });

      // Mouse up - end drag
      this.responseSigmaInstance.getMouseCaptor().on('mouseup', () => {
        if (draggedNode) {
          (this.responseGraphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.style.cursor = 'default';
      });

      // Mouse leave container - end drag
      this.responseSigmaInstance.getMouseCaptor().on('mouseleave', () => {
        if (draggedNode) {
          (this.responseGraphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.style.cursor = 'default';
      });

      this.responseSigmaInstance.refresh();
      console.log('✅ Node dragging enabled for response graph');

    } catch (error) {
      console.error('Failed to render response graph:', error);
    }
  }

  // Handle keyboard events in textarea
  handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
    // If Shift+Enter, allow default behavior (new line)
  }

  // Document deletion methods
  confirmDeleteDocument(document: Document, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.documentToDelete = document;
    this.showDeleteConfirm = true;
  }

  cancelDeleteDocument() {
    this.showDeleteConfirm = false;
    this.documentToDelete = null;
  }

  async deleteDocument() {
    if (!this.documentToDelete) return;
    
    this.isDeleting = true;
    const docId = this.documentToDelete.id;
    const docName = this.documentToDelete.filename;
    
    try {
      // Call backend API to delete document
      await firstValueFrom(this.api.delete(`/documents/${docId}`));
      
      console.log(`✅ Document deleted: ${docName}`);
      
      // Remove from local stores
      this.allDocuments = this.allDocuments.filter(d => d.id !== docId);
      this.currentDocuments = this.currentDocuments.filter(d => d.id !== docId);
      this.availableDocuments = this.availableDocuments.filter(d => d.id !== docId);
      
      // Remove from current session's document_ids if present
      if (this.currentSession && this.currentSession.document_ids.includes(docId)) {
        this.currentSession.document_ids = this.currentSession.document_ids.filter(id => id !== docId);
      }
      
      // Close delete dialog
      this.showDeleteConfirm = false;
      this.documentToDelete = null;
      
      // If we're viewing this document, go back to list
      if (this.selectedDocument?.id === docId) {
        this.selectedDocument = null;
        this.explorerView = 'list';
      }

      // Refresh filtered documents list
      this.filterAvailableDocuments();
      
    } catch (error) {
      console.error('Failed to delete document:', error);
      alert(`Failed to delete document: ${error}`);
    } finally {
      this.isDeleting = false;
    }
  }
}

