import { CommonModule } from '@angular/common';
import { Component, ElementRef, NgZone, OnDestroy, OnInit, Pipe, PipeTransform, Renderer2, ViewChild } from '@angular/core';
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
  graphUnavailable?: boolean;
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
  responseGraphLoadingMessageId: string | null = null;
  responseGraphError: string | null = null;
  
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
  currentGraphDocumentId: string | null = null;
  allGraphEntities: any[] = [];
  allGraphEdges: any[] = [];
  graphEntities: any[] = [];
  graphEdges: any[] = [];
  graphSearchQuery = '';
  graphSearchMatches = 0;
  graphSearchActive = false;
  flaggedEntityIds = new Set<string>(); // Track flagged entities
  showFlaggedOnly = false; // Filter graph to show only flagged entities
  documentRisks: any[] = [];
  riskSummary: any = null;
  riskChartOptions: EChartsOption = {};
  riskGraphData: Map<string, { entities: any[], edges: any[] }> = new Map(); // Store graph data for each risk
  selectedRiskForGraph: any = null; // Currently selected risk for graph view
  isRiskGraphFullscreen = false; // Risk graph fullscreen modal
  riskSigmaInstance: Sigma | null = null; // Separate Sigma instance for risk graphs
  riskGraphInstance: Graph | null = null; // Graphology instance for risk graph
  riskGraphLayout: 'force' | 'circular' | 'grid' | 'random' = 'force'; // Current layout for risk graph
  riskGraphSearchQuery = ''; // Search query for risk graph
  riskGraphEntities: any[] = []; // Filtered entities for risk graph
  riskGraphEdges: any[] = []; // Filtered edges for risk graph
  riskGraphSearchActive = false; // Whether search is active
  markdownHtml: SafeHtml | null = null;
  isMarkdownFullscreen = false;
  isPdfFullscreen = false;
  pdfTargetPage: number | undefined = undefined; // Target page for PDF navigation
  pdfCitedPages: number[] = []; // All pages cited for current document
  
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
  private speechRecognition: any = null;
  isListening = false;
  voiceSupport = false;
  isSpeaking = false;
  speakingMessageId: string | null = null;
  private preferredVoice?: SpeechSynthesisVoice;
  private voicesChangedHandler?: () => void;

  private citationClickHandler?: () => void;
  
  constructor(
    private api: ApiService, 
    private sanitizer: DomSanitizer, 
    private ngZone: NgZone,
    private renderer: Renderer2,
    private elementRef: ElementRef
  ) {
    // Customize markdown link renderer to handle citations with page numbers
    const defaultRender = this.markdownRenderer.renderer.rules.link_open || 
      ((tokens: any, idx: any, options: any, env: any, self: any) => self.renderToken(tokens, idx, options));
    
    this.markdownRenderer.renderer.rules.link_open = (tokens: any, idx: any, options: any, env: any, self: any) => {
      const token = tokens[idx];
      const hrefIndex = token.attrIndex('href');
      
      if (hrefIndex >= 0) {
        const href = token.attrs![hrefIndex][1];
        
        // Check if this is a citation link (e.g., doc:doc_abc123:47 or doc:doc_abc123 or document:doc_abc123:15,47,89)
        if (href.startsWith('doc:') || href.startsWith('document:')) {
          const citationData = href.replace(/^(doc:|document:)/, '');
          const parts = citationData.split(':');
          const docId = parts[0];
          const pageData = parts[1]; // Could be "47" or "15,47,89" or undefined/empty
          
          token.attrSet('class', 'citation-link');
          token.attrSet('data-doc-id', docId);
          token.attrSet('role', 'button');
          token.attrSet('tabindex', '0');
          
          // Parse page number(s) - support multiple pages and store metadata
          const uniquePages: number[] = [];
          const addUniquePage = (value: string | number | null | undefined) => {
            if (value === null || value === undefined) {
              return;
            }
            const num = typeof value === 'number' ? value : parseInt(String(value).trim(), 10);
            if (!isNaN(num) && num > 0 && !uniquePages.includes(num)) {
              uniquePages.push(num);
            }
          };
          
          if (pageData && pageData.trim()) {
            const pages = pageData.split(',').map((p: string) => p.trim());
            pages.forEach((p: string) => addUniquePage(p));
          }
          
          if (uniquePages.length > 0) {
            token.attrSet('data-page', uniquePages[0].toString());
            token.attrSet('data-pages', uniquePages.join(','));
            token.attrSet('title', uniquePages.length > 1 ? `Open pages ${uniquePages.join(', ')}` : `Open page ${uniquePages[0]}`);
          } else {
            token.attrSet('title', 'Open document');
          }
          
          token.attrSet('href', 'javascript:void(0)');
          return self.renderToken(tokens, idx, options);
        }
      }
      
      return defaultRender(tokens, idx, options, env, self);
    };

    this.initializeSpeechRecognition();
    this.initializeSpeechSynthesis();
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
    // Remove existing handler if any
    if (this.citationClickHandler) {
      this.citationClickHandler();
      this.citationClickHandler = undefined;
    }
    
    // Use event delegation to handle dynamically added citation links
    // Attach to the component's host element for better scoping
    this.citationClickHandler = this.renderer.listen(
      this.elementRef.nativeElement,
      'click',
      (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        
        // Try to find the citation link using closest() method (more reliable)
        const citationLink = target.closest('.citation-link') as HTMLElement | null;
        
        if (citationLink) {
          event.preventDefault();
          event.stopPropagation();
          
          const docId = citationLink.getAttribute('data-doc-id');
          let page: number | undefined;
          let citedPages: number[] | undefined;
          
          const pageAttr = citationLink.getAttribute('data-page');
          if (pageAttr) {
            const parsed = parseInt(pageAttr, 10);
            if (!isNaN(parsed) && parsed > 0) {
              page = parsed;
            }
          }
          
          const pagesAttr = citationLink.getAttribute('data-pages');
          if (pagesAttr) {
            const parsedPages = pagesAttr
              .split(',')
              .map(p => parseInt(p.trim(), 10))
              .filter(p => !isNaN(p) && p > 0);
            if (parsedPages.length > 0) {
              citedPages = parsedPages;
              if (page === undefined) {
                page = parsedPages[0];
              }
            }
          }
          
          if (!citedPages || citedPages.length === 0) {
            const text = (citationLink.textContent || '').replace(/\s+/g, ' ');
            const pageMatches = Array.from(text.matchAll(/page(?:s)?\s*(\d+)/gi)).map(match => parseInt(match[1], 10));
            const numberMatches = Array.from(text.matchAll(/\b(\d{1,4})\b/g)).map(match => parseInt(match[1], 10));
            
            const combined = [...pageMatches, ...numberMatches]
              .filter(num => !isNaN(num) && num > 0)
              .filter((num, idx, arr) => arr.indexOf(num) === idx);
            
            if (combined.length > 0) {
              citedPages = combined;
              if (page === undefined) {
                page = combined[0];
              }
              citationLink.setAttribute('data-pages', combined.join(','));
              citationLink.setAttribute('data-page', String(combined[0]));
            }
          }
          
          if (docId) {
            // Run inside Angular zone to trigger change detection
            this.ngZone.run(() => {
              this.openDocumentFromCitation(docId, page, citedPages);
            });
          } else {
            console.warn('Citation link clicked but no doc-id found', citationLink);
          }
        }
      }
    );
  }
  
  async openDocumentFromCitation(docId: string, page?: number, citedPages?: number[]) {
    let document = this.allDocuments.find(doc => doc.id === docId);
    
    // If the document is missing locally, refresh document list once
    if (!document) {
      await this.loadDocuments();
      document = this.allDocuments.find(doc => doc.id === docId);
    }
    
    if (!document) {
      return;
    }
    
    // If the document isn't yet attached to the active session, attach it automatically
    if (this.currentSession && !this.currentSession.document_ids.includes(document.id)) {
      await this.addExistingDocument(document);
    }
    
    // Ensure explorer is visible and show the PDF with page navigation
    this.showExplorer = true;
    this.viewDocumentPDF(document, page, citedPages);
  }

  // ---------------------------
  // Speech to Text
  // ---------------------------

  private initializeSpeechRecognition(): void {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition ||
      (window as any).mozSpeechRecognition ||
      (window as any).msSpeechRecognition;

    if (!SpeechRecognition) {
      return;
    }

    this.speechRecognition = new SpeechRecognition();
    this.speechRecognition.lang = 'en-US';
    this.speechRecognition.interimResults = false;
    this.speechRecognition.maxAlternatives = 1;

    this.speechRecognition.addEventListener('start', () => {
      this.ngZone.run(() => {
        this.isListening = true;
        this.userMessage = '';
      });
    });

    this.speechRecognition.addEventListener('end', () => {
      this.ngZone.run(() => {
        this.isListening = false;
      });
    });

    this.speechRecognition.addEventListener('error', () => {
      this.ngZone.run(() => {
        this.isListening = false;
      });
    });

    this.speechRecognition.addEventListener('result', (event: any) => {
      const recognitionEvent = event as any;
      const results = Array.from(recognitionEvent.results || []);
      const transcript = results
        .map((result: any) => (result[0]?.transcript ?? ''))
        .join(' ')
        .trim();

      this.ngZone.run(() => {
        if (transcript.length > 0) {
          this.userMessage = transcript;
          if (!this.isLoading && this.currentSession) {
            this.sendMessage();
          }
        }
      });
    });
  }

  toggleVoiceInput(): void {
    if (!this.speechRecognition || this.isLoading || !this.currentSession) {
      return;
    }

    if (this.isListening) {
      this.speechRecognition.stop();
    } else {
      try {
        this.speechRecognition.start();
      } catch (error) {
        this.isListening = false;
      }
    }
  }

  get isSpeechSupported(): boolean {
    return !!this.speechRecognition;
  }

  // ---------------------------
  // Speech Synthesis
  // ---------------------------

  private initializeSpeechSynthesis(): void {
    if (typeof window === 'undefined' || !(window as any).speechSynthesis || !(window as any).SpeechSynthesisUtterance) {
      this.voiceSupport = false;
      return;
    }

    this.voiceSupport = true;
    this.loadVoices();
    this.voicesChangedHandler = () => {
      this.ngZone.run(() => this.loadVoices());
    };
    window.speechSynthesis.addEventListener('voiceschanged', this.voicesChangedHandler);
  }

  private loadVoices(): void {
    if (!this.voiceSupport) {
      return;
    }
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) {
      return;
    }

    if (this.preferredVoice && voices.some(v => v.voiceURI === this.preferredVoice?.voiceURI)) {
      return;
    }

    const englishVoice = voices.find(v => v.lang?.toLowerCase().startsWith('en'));
    this.preferredVoice = englishVoice ?? voices[0];
  }

  speakAssistantMessage(message: ChatMessage): void {
    if (!this.voiceSupport || !message?.content) {
      return;
    }

    const plainText = this.extractPlainTextFromMarkdown(message.content);
    if (!plainText) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(plainText);
    if (this.preferredVoice) {
      utterance.voice = this.preferredVoice;
    }

    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onstart = () => {
      this.ngZone.run(() => {
        this.isSpeaking = true;
        this.speakingMessageId = message.id;
      });
    };

    const resetSpeakingState = () => {
      this.ngZone.run(() => {
        this.isSpeaking = false;
        this.speakingMessageId = null;
      });
    };

    utterance.onend = resetSpeakingState;
    utterance.onerror = resetSpeakingState;

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking(): void {
    if (!this.voiceSupport) {
      return;
    }
    window.speechSynthesis.cancel();
    this.isSpeaking = false;
    this.speakingMessageId = null;
  }

  private extractPlainTextFromMarkdown(markdown: string): string {
    try {
      const html = this.markdownRenderer.render(markdown || '');
      if (typeof window !== 'undefined' && (window as any).DOMParser) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        return doc?.body?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
      }
      return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    } catch (_error) {
      return markdown.replace(/[_*`~>\[\]#-]/g, ' ').replace(/\s+/g, ' ').trim();
    }
  }

  ngOnDestroy() {
    // Clean up citation click handler
    if (this.citationClickHandler) {
      this.citationClickHandler();
      this.citationClickHandler = undefined;
    }
    
    // Clean up Sigma instance to prevent memory leaks
    if (this.sigmaInstance) {
      try {
        this.sigmaInstance.kill();
        this.sigmaInstance = null;
      } catch (err) {
        console.warn('Error cleaning up Sigma instance:', err);
      }
    }

    if (this.speechRecognition) {
      try {
        this.speechRecognition.stop();
      } catch {
        // ignore
      }
      this.speechRecognition = null;
    }

    if (this.voicesChangedHandler && this.voiceSupport) {
      window.speechSynthesis.removeEventListener('voiceschanged', this.voicesChangedHandler);
    }

    this.stopSpeaking();
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
    const isDifferentDoc = this.currentGraphDocumentId !== doc.id;
    if (isDifferentDoc) {
      this.graphEntities = [];
      this.graphEdges = [];
      this.graphSearchQuery = '';
      this.graphSearchActive = false;
      this.graphSearchMatches = 0;
    }

    // Clear flagged entities when switching documents (but not on initial selection)
    const isDifferentDocument = this.selectedDocument && this.selectedDocument.id && this.selectedDocument.id !== doc.id;
    if (isDifferentDocument) {
      this.flaggedEntityIds.clear();
      this.showFlaggedOnly = false;
    }
    
    this.selectedDocument = doc;
    this.explorerView = 'graph';
    
    // Destroy existing Sigma instance
    if (this.sigmaInstance) {
      try {
        this.sigmaInstance.kill();
        this.sigmaInstance = null;
      } catch (err) {
        console.warn('Error destroying Sigma instance:', err);
      }
    }
    
    await this.loadGraphData(doc);
    this.applyGraphSearch();
  }

  private async loadGraphData(doc: Document, forceReload: boolean = false): Promise<void> {
    if (!doc.graph_id) {
      console.warn('No graph_id for document:', doc.id);
      this.currentGraphDocumentId = doc.id;
      this.allGraphEntities = [];
      this.allGraphEdges = [];
      this.resetGraphSearchState(false);
      return;
    }

    const isSameDoc = this.currentGraphDocumentId === doc.id;
    if (!forceReload && isSameDoc && this.allGraphEntities.length > 0) {
      return;
    }

    try {
      const entities = await firstValueFrom(this.api.get(`/entities/graph/${doc.graph_id}`));

      let relationships: any[] = [];
      try {
        relationships = await firstValueFrom(this.api.get(`/relationships/graph/${doc.graph_id}`));
        console.log('🔗 Raw relationships from API:', relationships.slice(0, 3));
      } catch (err) {
        console.warn('No relationships loaded:', err);
      }

      this.currentGraphDocumentId = doc.id;
      this.allGraphEntities = entities || [];
      this.allGraphEdges = relationships || [];
      console.log(`📊 Loaded ${this.allGraphEntities.length} entities and ${this.allGraphEdges.length} relationships for graph ${doc.graph_id}`);
      this.resetGraphSearchState(false);
    } catch (error) {
      console.error('Failed to load graph data:', error);
      this.allGraphEntities = [];
      this.allGraphEdges = [];
      this.resetGraphSearchState(false);
    }
  }

  private resetGraphSearchState(shouldRefresh: boolean = true): void {
    this.graphSearchQuery = '';
    this.graphSearchActive = false;
    this.graphEntities = [...this.allGraphEntities];
    this.graphEdges = [...this.allGraphEdges];
    this.graphSearchMatches = this.graphEntities.length;

    if (shouldRefresh) {
      this.refreshGraphVisualization();
    }
  }

  applyGraphSearch(): void {
    if (!this.allGraphEntities) {
      this.graphEntities = [];
      this.graphEdges = [];
      this.graphSearchMatches = 0;
      this.graphSearchActive = false;
      return;
    }

    // If flagged filter is active, use that instead
    if (this.showFlaggedOnly) {
      this.applyFlaggedFilter();
      return;
    }

    const query = (this.graphSearchQuery || '').trim().toLowerCase();

    if (!query) {
      this.graphSearchActive = false;
      this.graphEntities = [...this.allGraphEntities];
      this.graphEdges = [...this.allGraphEdges];
      this.graphSearchMatches = this.graphEntities.length;
    } else {
      const matchedEntities = this.allGraphEntities.filter((entity) => this.matchesEntity(entity, query));
      const matchedIds = new Set<string>();
      matchedEntities.forEach((entity) => {
        const id = this.getEntityId(entity);
        if (id) {
          matchedIds.add(id);
        }
      });

      this.graphSearchMatches = matchedIds.size;
      this.graphSearchActive = true;

      if (matchedIds.size === 0) {
        this.graphEntities = [];
        this.graphEdges = [];
      } else {
        const visibleIds = new Set<string>(matchedIds);

        this.allGraphEdges.forEach((edge) => {
          const { source, target } = this.getEdgeEndpoints(edge);
          if (!source || !target) {
            return;
          }
          if (matchedIds.has(source) || matchedIds.has(target)) {
            visibleIds.add(source);
            visibleIds.add(target);
          }
        });

        this.graphEntities = this.allGraphEntities.filter((entity) => {
          const id = this.getEntityId(entity);
          return !!id && visibleIds.has(id);
        });

        this.graphEdges = this.allGraphEdges.filter((edge) => {
          const { source, target } = this.getEdgeEndpoints(edge);
          return !!source && !!target && visibleIds.has(source) && visibleIds.has(target);
        });
      }
    }

    if (this.explorerView === 'graph' || this.isGraphFullscreen) {
      this.refreshGraphVisualization();
    }
  }

  clearGraphSearch(event?: Event): void {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (!this.graphSearchQuery) {
      return;
    }
    this.graphSearchQuery = '';
    this.applyGraphSearch();
  }

  toggleEntityFlag(entity: any, event?: Event): void {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const entityId = this.getEntityId(entity);
    if (!entityId) {
      return;
    }

    // Verify entity exists in allGraphEntities before flagging
    if (this.allGraphEntities && this.allGraphEntities.length > 0) {
      const exists = this.allGraphEntities.some(e => this.getEntityId(e) === entityId);
      if (!exists) {
        return;
      }
    }

    if (this.flaggedEntityIds.has(entityId)) {
      this.flaggedEntityIds.delete(entityId);
    } else {
      this.flaggedEntityIds.add(entityId);
    }

    // If showing flagged only, update the graph
    if (this.showFlaggedOnly) {
      this.applyFlaggedFilter();
    }
  }

  isEntityFlagged(entity: any): boolean {
    const entityId = this.getEntityId(entity);
    return entityId ? this.flaggedEntityIds.has(entityId) : false;
  }

  applyFlaggedFilter(): void {
    if (!this.showFlaggedOnly) {
      // If not filtering by flags, apply regular search (but avoid recursion)
      this.showFlaggedOnly = false; // Reset flag to prevent recursion
      this.applyGraphSearch();
      return;
    }
    
    if (this.flaggedEntityIds.size === 0) {
      // No flagged entities - show empty results
      this.graphEntities = [];
      this.graphEdges = [];
      if (this.explorerView === 'graph' || this.isGraphFullscreen) {
        this.refreshGraphVisualization();
      }
      return;
    }

    if (!this.allGraphEntities || !this.allGraphEdges) {
      this.graphEntities = [];
      this.graphEdges = [];
      return;
    }

    // Check if flagged IDs exist in allGraphEntities
    const allEntityIds = new Set(this.allGraphEntities.map(e => this.getEntityId(e)).filter((id): id is string => !!id));
    const matchingFlaggedIds = Array.from(this.flaggedEntityIds).filter(id => allEntityIds.has(id));

    // Start with flagged entities that exist in allGraphEntities
    const visibleIds = new Set<string>(matchingFlaggedIds);

    // Add all entities connected to flagged entities via edges
    const matchingFlaggedSet = new Set(matchingFlaggedIds);
    this.allGraphEdges.forEach((edge) => {
      const { source, target } = this.getEdgeEndpoints(edge);
      if (!source || !target) {
        return;
      }
      if (matchingFlaggedSet.has(source) || matchingFlaggedSet.has(target)) {
        visibleIds.add(source);
        visibleIds.add(target);
      }
    });

    // Filter entities to show only flagged and their connections
    this.graphEntities = this.allGraphEntities.filter((entity) => {
      const id = this.getEntityId(entity);
      return !!id && visibleIds.has(id);
    });

    // Filter edges to show only edges between visible entities
    this.graphEdges = this.allGraphEdges.filter((edge) => {
      const { source, target } = this.getEdgeEndpoints(edge);
      return !!source && !!target && visibleIds.has(source) && visibleIds.has(target);
    });

    // Apply search filter if active
    if (this.graphSearchQuery) {
      const query = this.graphSearchQuery.trim().toLowerCase();
      if (query) {
        const searchMatched = this.graphEntities.filter((entity) => this.matchesEntity(entity, query));
        const searchMatchedIds = new Set<string>();
        searchMatched.forEach((entity) => {
          const id = this.getEntityId(entity);
          if (id) searchMatchedIds.add(id);
        });

        // Include connections to search-matched entities
        this.graphEdges.forEach((edge) => {
          const { source, target } = this.getEdgeEndpoints(edge);
          if (source && target && (searchMatchedIds.has(source) || searchMatchedIds.has(target))) {
            searchMatchedIds.add(source);
            searchMatchedIds.add(target);
          }
        });

        this.graphEntities = this.graphEntities.filter((entity) => {
          const id = this.getEntityId(entity);
          return !!id && searchMatchedIds.has(id);
        });

        this.graphEdges = this.graphEdges.filter((edge) => {
          const { source, target } = this.getEdgeEndpoints(edge);
          return !!source && !!target && searchMatchedIds.has(source) && searchMatchedIds.has(target);
        });
      }
    }

    if (this.explorerView === 'graph' || this.isGraphFullscreen) {
      this.refreshGraphVisualization();
    }
  }

  toggleFlaggedFilter(): void {
    this.showFlaggedOnly = !this.showFlaggedOnly;
    if (this.showFlaggedOnly) {
      this.applyFlaggedFilter();
    } else {
      this.applyGraphSearch(); // Revert to regular search
    }
  }

  clearAllFlags(): void {
    this.flaggedEntityIds.clear();
    this.showFlaggedOnly = false;
    this.applyGraphSearch(); // Revert to regular view
  }

  private refreshGraphVisualization(): void {
    if (this.explorerView === 'graph') {
      setTimeout(() => this.renderSigmaGraph(false), 0);
    }
    if (this.isGraphFullscreen) {
      setTimeout(() => this.renderSigmaGraph(true), 0);
    }
  }

  private getEntityId(entity: any): string | undefined {
    if (!entity) return undefined;
    return entity.id || entity.entityId || entity.entity_id || entity.uuid;
  }

  getEntityDisplayType(entity: any): string {
    if (!entity) {
      return 'Entity';
    }

    const rawType = (entity.display_type || entity.displayType || '').toString().trim();
    if (rawType) {
      return rawType;
    }

    const type = (entity.type || entity.entityType || '').toString();
    const typeLower = type.toLowerCase();
    const props = entity.properties || entity.data || {};
    const name = (entity.name || '').toString();
    const propKeys = Object.keys(props || {}).map((key) => key.toLowerCase());
    const propValues = Object.values(props || {});

    const containsMetricKeyword = (text: string) =>
      /revenue|billings|gross margin|operating margin|earnings|diluted|guidance|subscription/i.test(text);

    if (propKeys.some((key) => key.includes('exhibit'))) {
      if (/press release/i.test(props.description || name)) {
        return 'Press Release';
      }
      if (/cover page/i.test(props.description || name)) {
        return 'Cover Page Exhibit';
      }
      return 'Exhibit';
    }

    if (/press release/i.test(name) || /press release/i.test(props.description || '')) {
      return 'Press Release';
    }

    if (/inline xbrl|cover page/i.test(name) || propKeys.some((key) => key.includes('inline'))) {
      return 'Inline XBRL';
    }

    if (containsMetricKeyword(name) || propKeys.some((key) => containsMetricKeyword(key))) {
      return 'Financial Metric';
    }

    const numericValueCount = propValues.filter((value) => {
      if (typeof value === 'number') return true;
      if (typeof value === 'string') {
        const numeric = value.replace(/[$,%\s]/g, '');
        return numeric !== '' && !Number.isNaN(Number(numeric));
      }
      return false;
    }).length;

    if (typeLower === 'location' && numericValueCount >= Math.max(1, propValues.length - 1)) {
      return 'Financial Metric';
    }

    return type || 'Entity';
  }

  private getEdgeEndpoints(edge: any): { source?: string; target?: string } {
    if (!edge) return {};
    const source =
      edge.from_entity_id ||
      edge.source ||
      edge.from ||
      edge.start ||
      edge.head ||
      edge.source_id ||
      edge.entitySourceId;
    const target =
      edge.to_entity_id ||
      edge.target ||
      edge.to ||
      edge.end ||
      edge.tail ||
      edge.target_id ||
      edge.entityTargetId;
    return { source, target };
  }

  private matchesEntity(entity: any, query: string): boolean {
    if (!entity) {
      return false;
    }

    const name = (entity.name || entity.label || '').toString().toLowerCase();
    if (name.includes(query)) {
      return true;
    }

    const type = (entity.type || entity.entityType || '').toString().toLowerCase();
    if (type.includes(query)) {
      return true;
    }

    const displayType = this.getEntityDisplayType(entity).toLowerCase();
    if (displayType.includes(query)) {
      return true;
    }

    const properties = entity.properties || entity.data || {};
    if (properties && typeof properties === 'object') {
      for (const [key, value] of Object.entries(properties)) {
        if (value === null || value === undefined) {
          continue;
        }

        const keyStr = String(key).toLowerCase();
        if (keyStr.includes(query)) {
          return true;
        }

        let valueStr = '';
        if (typeof value === 'string') {
          valueStr = value.toLowerCase();
        } else if (typeof value === 'number' || typeof value === 'boolean') {
          valueStr = String(value).toLowerCase();
        } else if (Array.isArray(value)) {
          valueStr = value.map((item) => String(item).toLowerCase()).join(' ');
        } else if (typeof value === 'object') {
          valueStr = JSON.stringify(value).toLowerCase();
        }

        if (valueStr.includes(query)) {
          return true;
        }
      }
    }

    return false;
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
      
      // Remove existing tooltips if any
      ['node-tooltip', 'edge-tooltip'].forEach((id) => {
        const existing = document.getElementById(id);
        if (existing && existing.parentElement) {
          existing.parentElement.removeChild(existing);
        }
      });
      
      // Add nodes (positions will be set by layout algorithm)
      console.log('🔵 Adding nodes to graph...');
      const MAX_NODE_TOOLTIP_PROPS = 5;
      this.graphEntities.forEach((entity) => {
        const props = entity.properties || {};
        const description = Object.entries(props)
          .filter(([key, value]) => value !== null && value !== undefined && String(value).trim() !== '')
          .slice(0, MAX_NODE_TOOLTIP_PROPS)
          .map(([key, value]) => {
            let displayValue = value;
            if (typeof value === 'number' && Math.abs(value) >= 1000) {
              displayValue = new Intl.NumberFormat().format(value);
            }
            return `${this.formatLabel(key)}: ${displayValue}`;
          })
          .join('\n');

        (this.graphInstance as any).addNode(entity.id, {
          label: entity.name,
          x: 0,
          y: 0,
          size: 8,
          color: typeColors[entity.type] || '#94a3b8',
          description
        });
      });
      console.log(`✅ Added ${this.graphEntities.length} nodes`);
      
      // Add edges with metadata
      console.log('🔗 Adding edges to graph...');
      const normalizedEdges: Array<{
        key: string;
        from: string;
        to: string;
        label: string;
        properties: Record<string, any>;
      }> = [];
      const edgeDataByKey = new Map<string, any>();
      const MAX_EDGE_TOOLTIP_PROPS = 5;
      
      this.graphEdges.forEach((edge) => {
        const sourceId = edge.from_entity_id || edge.source || edge.from || edge.start || edge.head;
        const targetId = edge.to_entity_id || edge.target || edge.to || edge.end || edge.tail;
        if (!sourceId || !targetId) {
          return;
        }
        
        const label = edge.relationship_type || edge.type || edge.label || 'RELATED_TO';
        const properties: Record<string, any> = { ...(edge.properties || {}) };
        if (edge.reasoning && !properties['reasoning']) {
          properties['reasoning'] = edge.reasoning;
        }
        if (edge.explanation && !properties['explanation']) {
          properties['explanation'] = edge.explanation;
        }
        if (edge.confidence !== undefined && properties['confidence'] === undefined) {
          properties['confidence'] = edge.confidence;
        }
        if (edge.impact && !properties['impact']) {
          properties['impact'] = edge.impact;
        }
        if (edge.citations && !properties['citations']) {
          properties['citations'] = edge.citations;
        }
        if (edge.detected_by && !properties['detected_by']) {
          properties['detected_by'] = edge.detected_by;
        }

        const edgeKey = `edge_${normalizedEdges.length}`;
        normalizedEdges.push({
          key: edgeKey,
          from: sourceId,
          to: targetId,
          label,
          properties
        });
        edgeDataByKey.set(edgeKey, {
          ...edge,
          relationship_type: label,
          from_entity_id: sourceId,
          to_entity_id: targetId,
          properties
        });
      });
      
      let edgesAdded = 0;
      let edgesSkipped = 0;
      normalizedEdges.forEach((edge) => {
        try {
          const hasSource = (this.graphInstance as any).hasNode(edge.from);
          const hasTarget = (this.graphInstance as any).hasNode(edge.to);
          
          if (hasSource && hasTarget) {
            (this.graphInstance as any).addEdgeWithKey(
              edge.key,
              edge.from,
              edge.to,
              {
                label: edge.label || 'RELATED_TO',
                size: 2,
                color: '#ef4444',
                type: 'arrow',
                description: Object.entries(edge.properties || {})
                  .filter(([key, value]) => value !== null && value !== undefined && String(value).trim() !== '')
                  .slice(0, MAX_EDGE_TOOLTIP_PROPS)
                  .map(([key, value]) => `${this.formatLabel(key)}: ${value}`)
                  .join('\n')
              }
            );
            edgesAdded++;
          } else {
            edgesSkipped++;
          }
        } catch (err) {
          console.error(`   ❌ Failed to add edge ${edge.from} -> ${edge.to}:`, err);
        }
      });
      
      console.log(`✅ Added ${edgesAdded} edges (skipped ${edgesSkipped}) out of ${normalizedEdges.length} total`);
      
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
      
      // Enable node dragging with tooltips
      let draggedNode: string | null = null;
      let isDragging = false;
      
      this.sigmaInstance.on('downNode', (e: any) => {
        isDragging = true;
        draggedNode = e.node;
        (this.graphInstance as any).setNodeAttribute(draggedNode, 'highlighted', true);
        container.nativeElement.style.cursor = 'grabbing';

        const attrs = (this.graphInstance as any).getNodeAttributes(draggedNode);
        const description = attrs?.description;
        if (description) {
          let tooltip = document.getElementById('node-tooltip');
          if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'node-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = 'rgba(31,41,55,0.95)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '12px';
            tooltip.style.maxWidth = '260px';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '10000';
            tooltip.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            document.body.appendChild(tooltip);
          }
          tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
            <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
          `;
          tooltip.style.display = 'block';
          const updateTooltipPosition = (evt: MouseEvent) => {
            if (tooltip) {
              tooltip.style.left = (evt.clientX + 15) + 'px';
              tooltip.style.top = (evt.clientY + 15) + 'px';
            }
          };
          container.nativeElement.addEventListener('mousemove', updateTooltipPosition);
          (tooltip as any)._removeListener = () => {
            container.nativeElement.removeEventListener('mousemove', updateTooltipPosition);
          };
        }
      });
      
      this.sigmaInstance.on('enterNode', (event: any) => {
        container.nativeElement.style.cursor = 'grab';
        const nodeId = event.node;
        const attrs = (this.graphInstance as any).getNodeAttributes(nodeId);
        const description = attrs?.description;
        if (description) {
          let tooltip = document.getElementById('node-tooltip');
          if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'node-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = 'rgba(31,41,55,0.95)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '12px';
            tooltip.style.maxWidth = '260px';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '10000';
            tooltip.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            document.body.appendChild(tooltip);
          }
          tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
            <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
          `;
          tooltip.style.display = 'block';
          const updateTooltipPosition = (evt: MouseEvent) => {
            if (tooltip) {
              tooltip.style.left = (evt.clientX + 15) + 'px';
              tooltip.style.top = (evt.clientY + 15) + 'px';
            }
          };
          container.nativeElement.addEventListener('mousemove', updateTooltipPosition);
          (tooltip as any)._removeListener = () => {
            container.nativeElement.removeEventListener('mousemove', updateTooltipPosition);
          };
        }
      });
      
      this.sigmaInstance.on('leaveNode', () => {
        if (!isDragging) {
          container.nativeElement.style.cursor = 'default';
        }
        const tooltip = document.getElementById('node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });
      
      // Edge hover - show relationship details in tooltip
      this.sigmaInstance.on('enterEdge', (event: any) => {
        const edgeKey = event.edge;
        const edgeData = edgeDataByKey.get(edgeKey);
        if (!edgeData) {
          return;
        }
        
        const props = edgeData.properties || {};
        const reasoning = props['reasoning'] || props['explanation'] || edgeData.reasoning || edgeData.explanation || 'No reasoning provided';
        const impact = props['impact'] || props['effect'];
        const confidenceValue = props['confidence'] ?? edgeData.confidence;
        const confidence = typeof confidenceValue === 'number'
          ? ` (confidence: ${(confidenceValue * 100).toFixed(0)}%)`
          : (confidenceValue ? ` (confidence: ${confidenceValue})` : '');
        const detectedBy = props['detected_by'] || props['source'] || edgeData.detected_by || 'unknown';
        const citations = Array.isArray(props['citations']) ? props['citations'] : [];
        
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
          tooltip.style.maxWidth = '320px';
          tooltip.style.zIndex = '10000';
          tooltip.style.pointerEvents = 'none';
          tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
          document.body.appendChild(tooltip);
        }
        
        tooltip.innerHTML = `
          <div style="margin-bottom: 4px"><strong>${edgeData.relationship_type || 'RELATIONSHIP'}</strong></div>
          <div style="color: #d1d5db; font-size: 11px">${reasoning}${confidence}</div>
          ${impact ? `<div style="color:#fbbf24;font-size:11px;margin-top:4px">Impact: ${impact}</div>` : ''}
          <div style="color: #9ca3af; font-size: 10px; margin-top: 4px">Detected by: ${detectedBy}</div>
          ${citations.length > 0 ? `<div style="color:#9ca3af;font-size:10px;margin-top:4px">Citation: ${citations[0]}</div>` : ''}
        `;
        tooltip.style.display = 'block';
        
        const updateTooltipPosition = (evt: MouseEvent) => {
          if (tooltip) {
            tooltip.style.left = (evt.clientX + 15) + 'px';
            tooltip.style.top = (evt.clientY + 15) + 'px';
          }
        };
        
        container.nativeElement.addEventListener('mousemove', updateTooltipPosition);
        (tooltip as any)._removeListener = () => {
          container.nativeElement.removeEventListener('mousemove', updateTooltipPosition);
        };
      });
      
      this.sigmaInstance.on('leaveEdge', () => {
        const tooltip = document.getElementById('edge-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });
      
      this.sigmaInstance.on('clickEdge', (event: any) => {
        const edgeKey = event.edge;
        const edgeData = edgeDataByKey.get(edgeKey);
        if (!edgeData) {
          return;
        }
        
        console.group('🔗 Relationship Details');
        console.log('Type:', edgeData.relationship_type || 'RELATIONSHIP');
        console.log('From:', edgeData.from_entity_id);
        console.log('To:', edgeData.to_entity_id);
        console.log('Properties:', edgeData.properties);
        console.groupEnd();
        
        (this.graphInstance as any).setEdgeAttribute(edgeKey, 'color', '#3b82f6');
        setTimeout(() => {
          (this.graphInstance as any).setEdgeAttribute(edgeKey, 'color', '#ef4444');
        }, 2000);
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
        const tooltip = document.getElementById('node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });
      
      // Mouse leave container - end drag
      this.sigmaInstance.getMouseCaptor().on('mouseleave', () => {
        if (draggedNode) {
          (this.graphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.nativeElement.style.cursor = 'default';
        const tooltip = document.getElementById('node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
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
    const isDifferentDoc = this.currentGraphDocumentId !== doc.id;
    if (isDifferentDoc) {
      this.graphEntities = [];
      this.graphEdges = [];
      this.graphSearchQuery = '';
      this.graphSearchActive = false;
      this.graphSearchMatches = 0;
    }

    this.selectedDocument = doc;
    this.explorerView = 'entities';
    
    await this.loadGraphData(doc);
    this.applyGraphSearch();
  }

  async viewDocumentRisks(doc: Document) {
    this.selectedDocument = doc;
    this.explorerView = 'risks';
    this.documentRisks = [];
    this.riskSummary = null;
    this.riskChartOptions = {};
    this.riskGraphData.clear();
    
    try {
      // Load risks for document
      const response = await firstValueFrom(
        this.api.get(`/risks/document/${doc.id}`)
      );
      this.documentRisks = response.risks || [];
      this.riskSummary = response.summary || null;
      console.log(`Loaded ${this.documentRisks.length} risks for document ${doc.id}`);
      
      // Load graph data for each risk's affected entities (after risks are loaded)
      if (doc.graph_id && this.documentRisks.length > 0) {
        await this.loadRiskGraphData(doc.graph_id);
      }
      
      // Generate risk chart (reset first to avoid ECharts initialization error)
      this.riskChartOptions = {};
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

  async loadRiskGraphData(graphId: string): Promise<void> {
    // Graph data is already persisted with risks - just extract it
    this.riskGraphData.clear();
    
    for (const risk of this.documentRisks) {
      if (!risk.id) {
        continue;
      }
      
      // Use persisted graph_data from risk
      const graphData = risk.graph_data;
      if (graphData && graphData.entities) {
        // Deduplicate entities by both ID and name
        const entityMapById = new Map<string, any>();
        const seenNames = new Set<string>();
        
        (graphData.entities || []).forEach((e: any) => {
          const id = e.id || e.entityId || e.entity_id;
          const name = (e.name || '').trim().toLowerCase();
          
          if (id && typeof id === 'string' && !entityMapById.has(id)) {
            // Check for duplicate names
            if (!name || !seenNames.has(name)) {
              entityMapById.set(id, e);
              if (name) {
                seenNames.add(name);
              }
            }
          }
        });
        
        this.riskGraphData.set(risk.id, {
          entities: Array.from(entityMapById.values()),
          edges: graphData.relationships || []
        });
      } else {
        // No graph data available
        this.riskGraphData.set(risk.id, {
          entities: [],
          edges: []
        });
      }
    }
  }

  getAffectedEntitiesForRisk(risk: any): any[] {
    const graphData = this.riskGraphData.get(risk.id);
    if (!graphData || !graphData.entities || graphData.entities.length === 0) {
      return [];
    }
    
    const affectedIds = new Set<string>(risk.affected_entity_ids || []);
    const entityMapById = new Map<string, any>();
    const seenNames = new Set<string>();
    
    // First, prioritize entities that are directly affected (from affected_entity_ids)
    // Then include other entities from the LLM-generated graph
    const allEntities = graphData.entities;
    
    // Sort: affected entities first, then others
    const sortedEntities = [...allEntities].sort((a, b) => {
      const aId = a.id || a.entityId || a.entity_id;
      const bId = b.id || b.entityId || b.entity_id;
      const aIsAffected = aId && affectedIds.has(aId);
      const bIsAffected = bId && affectedIds.has(bId);
      
      if (aIsAffected && !bIsAffected) return -1;
      if (!aIsAffected && bIsAffected) return 1;
      return 0;
    });
    
    // Filter and deduplicate entities by both ID and name
    sortedEntities.forEach((e: any) => {
      const id = e.id || e.entityId || e.entity_id;
      const name = (e.name || '').trim().toLowerCase();
      
      if (id && typeof id === 'string') {
        // Deduplicate by ID
        if (!entityMapById.has(id)) {
          // Also check for duplicate names
          if (!name || !seenNames.has(name)) {
            entityMapById.set(id, e);
            if (name) {
              seenNames.add(name);
            }
          }
        }
      }
    });
    
    return Array.from(entityMapById.values());
  }

  hasRiskGraphData(risk: any): boolean {
    const graphData = this.riskGraphData.get(risk.id);
    return !!(graphData && graphData.entities && graphData.entities.length > 0);
  }

  getRiskGraphEntityCount(riskId: string): number {
    const graphData = this.riskGraphData.get(riskId);
    return graphData?.entities?.length || 0;
  }

  getRiskGraphEdgeCount(riskId: string): number {
    if (this.riskGraphSearchActive && this.riskGraphEdges.length > 0) {
      return this.riskGraphEdges.length;
    }
    const graphData = this.riskGraphData.get(riskId);
    return graphData?.edges?.length || 0;
  }

  getRiskGraphEntityCountFiltered(riskId: string): number {
    if (this.riskGraphSearchActive && this.riskGraphEntities.length > 0) {
      return this.riskGraphEntities.length;
    }
    return this.getRiskGraphEntityCount(riskId);
  }

  openRiskGraphView(risk: any): void {
    this.selectedRiskForGraph = risk;
    this.isRiskGraphFullscreen = true;
    this.riskGraphSearchQuery = '';
    this.riskGraphSearchActive = false;
    
    // Initialize filtered arrays with all data
    const graphData = this.riskGraphData.get(risk.id);
    if (graphData) {
      this.riskGraphEntities = [...graphData.entities];
      this.riskGraphEdges = [...graphData.edges];
    }
    
    // Render graph after modal opens
    setTimeout(() => {
      this.renderRiskGraph(risk);
    }, 100);
  }

  closeRiskGraphView(): void {
    this.isRiskGraphFullscreen = false;
    this.selectedRiskForGraph = null;
    this.riskGraphSearchQuery = '';
    this.riskGraphSearchActive = false;
    
    // Clean up tooltips
    const nodeTooltip = document.getElementById('risk-node-tooltip');
    if (nodeTooltip) {
      nodeTooltip.remove();
    }
    const edgeTooltip = document.getElementById('risk-edge-tooltip');
    if (edgeTooltip) {
      edgeTooltip.remove();
    }
    
    // Clean up risk graph instance
    if (this.riskSigmaInstance) {
      try {
        this.riskSigmaInstance.kill();
        this.riskSigmaInstance = null;
      } catch (e) {
        // Ignore
      }
    }
    
    // Clean up graph instance
    this.riskGraphInstance = null;
  }

  applyRiskGraphSearch(): void {
    if (!this.selectedRiskForGraph) return;
    
    const query = this.riskGraphSearchQuery.trim().toLowerCase();
    this.riskGraphSearchActive = query.length > 0;
    
    if (!this.riskGraphSearchActive) {
      // Reset to all entities/edges
      const graphData = this.riskGraphData.get(this.selectedRiskForGraph.id);
      if (graphData) {
        this.riskGraphEntities = [...graphData.entities];
        this.riskGraphEdges = [...graphData.edges];
      }
      this.renderRiskGraph(this.selectedRiskForGraph);
      return;
    }
    
    // Filter entities
    const graphData = this.riskGraphData.get(this.selectedRiskForGraph.id);
    if (!graphData) return;
    
    const matchingEntities = graphData.entities.filter((e: any) => {
      const name = (e.name || '').toLowerCase();
      const type = (e.type || '').toLowerCase();
      const displayType = (e.display_type || '').toLowerCase();
      return name.includes(query) || type.includes(query) || displayType.includes(query);
    });
    
    const matchingEntityIds = new Set(matchingEntities.map((e: any) => e.id || e.entityId || e.entity_id));
    
    // Filter edges to show only those connecting matching entities
    const matchingEdges = graphData.edges.filter((edge: any) => {
      const { source, target } = this.getEdgeEndpoints(edge);
      return matchingEntityIds.has(source) && matchingEntityIds.has(target);
    });
    
    this.riskGraphEntities = matchingEntities;
    this.riskGraphEdges = matchingEdges;
    
    // Re-render with filtered data
    this.renderRiskGraph(this.selectedRiskForGraph);
  }

  clearRiskGraphSearch(): void {
    this.riskGraphSearchQuery = '';
    this.riskGraphSearchActive = false;
    this.applyRiskGraphSearch();
  }

  changeRiskGraphLayout(layout: 'force' | 'circular' | 'grid' | 'random'): void {
    this.riskGraphLayout = layout;
    if (this.riskGraphInstance && this.riskSigmaInstance) {
      this.applyLayout(this.riskGraphInstance, layout);
      this.riskSigmaInstance.refresh();
    }
  }

  renderRiskGraph(risk: any): void {
    const graphData = this.riskGraphData.get(risk.id);
    if (!graphData || graphData.entities.length === 0) {
      console.warn('No graph data for risk:', risk.id);
      return;
    }
    
    const containerId = 'riskGraphContainer';
    const container = document.getElementById(containerId);
    if (!container) {
      console.error('Risk graph container not found');
      return;
    }
    
    // Clear existing risk graph
    if (this.riskSigmaInstance) {
      try {
        this.riskSigmaInstance.kill();
        this.riskSigmaInstance = null;
      } catch (e) {
        // Ignore
      }
    }
    
    // Clear graph instance
    this.riskGraphInstance = null;
    
    // Use filtered entities/edges if search is active, otherwise use all
    const entitiesToRender = this.riskGraphSearchActive && this.riskGraphEntities.length > 0
      ? this.riskGraphEntities
      : graphData.entities;
    const edgesToRender = this.riskGraphSearchActive && this.riskGraphEdges.length > 0
      ? this.riskGraphEdges
      : graphData.edges;
    
    // Create new graphology instance
    this.riskGraphInstance = new Graph();
    const graph = this.riskGraphInstance as any;
    
    // Map to store edge data for tooltips
    const edgeDataByKey = new Map<string, any>();
    
    // Add nodes (entities)
    entitiesToRender.forEach((entity: any) => {
      const id = entity.id || entity.entityId || entity.entity_id;
      if (!id || typeof id !== 'string') return;
      
      const isAffected = (risk.affected_entity_ids || []).includes(id);
      const displayType = this.getEntityDisplayType(entity);
      const type = entity.type || entity.entityType || 'Entity';
      const typeColors: { [key: string]: string } = {
        'Company': '#3b82f6',
        'Person': '#8b5cf6',
        'Location': '#10b981',
        'Metric': '#f59e0b',
        'Clause': '#ef4444',
        'Instrument': '#ec4899',
        'Entity': '#94a3b8'
      };
      
      // Build description for tooltip
      const props = entity.properties || {};
      const propEntries = Object.entries(props).slice(0, 5);
      const propText = propEntries.map(([k, v]) => `${k}: ${v}`).join('\n');
      const description = `${displayType}\n${propText ? propText : 'No additional properties'}`;
      
      graph.addNode(id, {
        label: entity.name || id,
        size: isAffected ? 12 : 8,
        color: isAffected ? '#ef4444' : (typeColors[type] || '#94a3b8'),
        description: description,
        x: Math.random() * 100,
        y: Math.random() * 100
      });
    });
    
    // Add edges (relationships)
    edgesToRender.forEach((edge: any) => {
      const { source, target } = this.getEdgeEndpoints(edge);
      if (!source || !target || typeof source !== 'string' || typeof target !== 'string') {
        return;
      }
      if (!graph.hasNode(source) || !graph.hasNode(target)) {
        return;
      }
      
      // Check if edge already exists (both directions for undirected)
      const edgeExists = graph.hasEdge(source, target) || graph.hasEdge(target, source);
      if (!edgeExists) {
        const edgeKey = graph.addEdge(source, target, {
          label: edge.type || edge.relationship_type || 'RELATED_TO',
          size: 2,
          color: '#94a3b8'
        });
        // Store edge data for tooltips
        edgeDataByKey.set(edgeKey, {
          relationship_type: edge.type || edge.relationship_type || 'RELATED_TO',
          properties: edge.properties || {},
          reasoning: edge.reasoning || edge.explanation,
          confidence: edge.confidence,
          detected_by: edge.detected_by || edge.source
        });
      }
    });
    
    // Apply layout based on current layout setting
    random.assign(graph, { scale: 100 }); // Start with random positions
    this.applyLayout(graph, this.riskGraphLayout);
    
    // Create Sigma instance for risk graph
    this.riskSigmaInstance = new Sigma(graph, container, {
      renderLabels: true,
      labelSize: 10,
      labelWeight: 'normal',
      labelColor: { attribute: 'color' },
      defaultNodeColor: '#10b981',
      defaultEdgeColor: '#94a3b8',
      minCameraRatio: 0.1,
      maxCameraRatio: 10
    });
    
    // Enable node dragging with tooltips (same as main graph)
    let draggedNode: string | null = null;
    let isDragging = false;
    
    this.riskSigmaInstance.on('downNode', (e: any) => {
      isDragging = true;
      draggedNode = e.node;
      (this.riskGraphInstance as any).setNodeAttribute(draggedNode, 'highlighted', true);
      container.style.cursor = 'grabbing';

      const attrs = (this.riskGraphInstance as any).getNodeAttributes(draggedNode);
      const description = attrs?.description;
      if (description) {
        let tooltip = document.getElementById('risk-node-tooltip');
        if (!tooltip) {
          tooltip = document.createElement('div');
          tooltip.id = 'risk-node-tooltip';
          tooltip.style.position = 'fixed';
          tooltip.style.backgroundColor = 'rgba(31,41,55,0.95)';
          tooltip.style.color = 'white';
          tooltip.style.padding = '8px 12px';
          tooltip.style.borderRadius = '6px';
          tooltip.style.fontSize = '12px';
          tooltip.style.maxWidth = '260px';
          tooltip.style.pointerEvents = 'none';
          tooltip.style.zIndex = '10000';
          tooltip.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
          document.body.appendChild(tooltip);
        }
        tooltip.innerHTML = `
          <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
          <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
        `;
        tooltip.style.display = 'block';
        const updateTooltipPosition = (evt: MouseEvent) => {
          if (tooltip) {
            tooltip.style.left = (evt.clientX + 15) + 'px';
            tooltip.style.top = (evt.clientY + 15) + 'px';
          }
        };
        container.addEventListener('mousemove', updateTooltipPosition);
        (tooltip as any)._removeListener = () => {
          container.removeEventListener('mousemove', updateTooltipPosition);
        };
      }
    });
    
    this.riskSigmaInstance.on('enterNode', (event: any) => {
      if (!isDragging) {
        container.style.cursor = 'grab';
      }
      const nodeId = event.node;
      const attrs = (this.riskGraphInstance as any).getNodeAttributes(nodeId);
      const description = attrs?.description;
      if (description && !isDragging) {
        let tooltip = document.getElementById('risk-node-tooltip');
        if (!tooltip) {
          tooltip = document.createElement('div');
          tooltip.id = 'risk-node-tooltip';
          tooltip.style.position = 'fixed';
          tooltip.style.backgroundColor = 'rgba(31,41,55,0.95)';
          tooltip.style.color = 'white';
          tooltip.style.padding = '8px 12px';
          tooltip.style.borderRadius = '6px';
          tooltip.style.fontSize = '12px';
          tooltip.style.maxWidth = '260px';
          tooltip.style.pointerEvents = 'none';
          tooltip.style.zIndex = '10000';
          tooltip.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
          document.body.appendChild(tooltip);
        }
        tooltip.innerHTML = `
          <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
          <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
        `;
        tooltip.style.display = 'block';
        const updateTooltipPosition = (evt: MouseEvent) => {
          if (tooltip) {
            tooltip.style.left = (evt.clientX + 15) + 'px';
            tooltip.style.top = (evt.clientY + 15) + 'px';
          }
        };
        container.addEventListener('mousemove', updateTooltipPosition);
        (tooltip as any)._removeListener = () => {
          container.removeEventListener('mousemove', updateTooltipPosition);
        };
      }
    });
    
    this.riskSigmaInstance.on('leaveNode', () => {
      if (!isDragging) {
        container.style.cursor = 'default';
      }
      const tooltip = document.getElementById('risk-node-tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
        if ((tooltip as any)._removeListener) {
          (tooltip as any)._removeListener();
        }
      }
    });
    
    this.riskSigmaInstance.getMouseCaptor().on('mousemovebody', (e: any) => {
      if (!isDragging || !draggedNode || !this.riskSigmaInstance || !this.riskGraphInstance) return;
      
      // Get new position from mouse
      const pos = this.riskSigmaInstance.viewportToGraph(e);
      
      // Update node position
      (this.riskGraphInstance as any).setNodeAttribute(draggedNode, 'x', pos.x);
      (this.riskGraphInstance as any).setNodeAttribute(draggedNode, 'y', pos.y);
      
      // Prevent camera movement while dragging
      e.preventSigmaDefault();
      e.original.preventDefault();
      e.original.stopPropagation();
    });
    
    this.riskSigmaInstance.getMouseCaptor().on('mouseup', () => {
      if (draggedNode && this.riskGraphInstance) {
        (this.riskGraphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
        draggedNode = null;
      }
      isDragging = false;
      if (container) {
        container.style.cursor = 'default';
      }
      const tooltip = document.getElementById('risk-node-tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
        if ((tooltip as any)._removeListener) {
          (tooltip as any)._removeListener();
        }
      }
    });
    
    // Edge hover - show relationship details in tooltip
    this.riskSigmaInstance.on('enterEdge', (event: any) => {
      const edgeKey = event.edge;
      const edgeData = edgeDataByKey.get(edgeKey);
      if (!edgeData) {
        return;
      }
      
      const props = edgeData.properties || {};
      const reasoning = props['reasoning'] || props['explanation'] || edgeData.reasoning || edgeData.explanation || 'No reasoning provided';
      const impact = props['impact'] || props['effect'];
      const confidenceValue = props['confidence'] ?? edgeData.confidence;
      const confidence = typeof confidenceValue === 'number'
        ? ` (confidence: ${(confidenceValue * 100).toFixed(0)}%)`
        : (confidenceValue ? ` (confidence: ${confidenceValue})` : '');
      const detectedBy = props['detected_by'] || props['source'] || edgeData.detected_by || 'unknown';
      const citations = Array.isArray(props['citations']) ? props['citations'] : [];
      
      let tooltip = document.getElementById('risk-edge-tooltip');
      if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'risk-edge-tooltip';
        tooltip.style.position = 'fixed';
        tooltip.style.backgroundColor = 'rgba(31, 41, 55, 0.95)';
        tooltip.style.color = 'white';
        tooltip.style.padding = '8px 12px';
        tooltip.style.borderRadius = '6px';
        tooltip.style.fontSize = '12px';
        tooltip.style.maxWidth = '320px';
        tooltip.style.zIndex = '10000';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
        document.body.appendChild(tooltip);
      }
      
      tooltip.innerHTML = `
        <div style="margin-bottom: 4px"><strong>${edgeData.relationship_type || 'RELATIONSHIP'}</strong></div>
        <div style="color: #d1d5db; font-size: 11px">${reasoning}${confidence}</div>
        ${impact ? `<div style="color:#fbbf24;font-size:11px;margin-top:4px">Impact: ${impact}</div>` : ''}
        <div style="color: #9ca3af; font-size: 10px; margin-top: 4px">Detected by: ${detectedBy}</div>
        ${citations.length > 0 ? `<div style="color:#9ca3af;font-size:10px;margin-top:4px">Citation: ${citations[0]}</div>` : ''}
      `;
      tooltip.style.display = 'block';
      
      const updateTooltipPosition = (evt: MouseEvent) => {
        if (tooltip) {
          tooltip.style.left = (evt.clientX + 15) + 'px';
          tooltip.style.top = (evt.clientY + 15) + 'px';
        }
      };
      
      container.addEventListener('mousemove', updateTooltipPosition);
      (tooltip as any)._removeListener = () => {
        container.removeEventListener('mousemove', updateTooltipPosition);
      };
    });
    
    this.riskSigmaInstance.on('leaveEdge', () => {
      const tooltip = document.getElementById('risk-edge-tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
        if ((tooltip as any)._removeListener) {
          (tooltip as any)._removeListener();
        }
      }
    });
  }

  async viewDocumentPDF(doc: Document, page?: number, citedPages?: number[]) {
    this.selectedDocument = doc;
    this.explorerView = 'pdf';
    
    const normalizedPages: number[] = [];
    const addPage = (value: number | string | null | undefined) => {
      if (value === null || value === undefined) {
        return;
      }
      const num = typeof value === 'number' ? value : parseInt(String(value).trim(), 10);
      if (!isNaN(num) && num > 0 && !normalizedPages.includes(num)) {
        normalizedPages.push(num);
      }
    };
    
    if (Array.isArray(citedPages) && citedPages.length > 0) {
      citedPages.forEach((p) => addPage(p));
    }
    
    if (page !== undefined) {
      addPage(page);
    }
    
    this.pdfCitedPages = normalizedPages;
    
    if (page !== undefined && !isNaN(page) && page > 0) {
      this.pdfTargetPage = page;
    } else if (normalizedPages.length > 0) {
      this.pdfTargetPage = normalizedPages[0];
    } else {
      this.pdfTargetPage = undefined;
    }
  }
  
  navigateToCitedPage(pageIndex: number) {
    if (pageIndex >= 0 && pageIndex < this.pdfCitedPages.length) {
      this.pdfTargetPage = this.pdfCitedPages[pageIndex];
    }
  }
  
  getCurrentCitedPageIndex(): number {
    if (this.pdfTargetPage && this.pdfCitedPages.length > 0) {
      return this.pdfCitedPages.indexOf(this.pdfTargetPage);
    }
    return -1;
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

  private formatLabel(key: string): string {
    if (!key) {
      return '';
    }
    return key
      .replace(/[_\-\s]+/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
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

  openPdfFullscreen() {
    if (!this.selectedDocument) {
      return;
    }
    this.isPdfFullscreen = true;
  }

  closePdfFullscreen() {
    this.isPdfFullscreen = false;
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

  private async ensureResponseGraphData(message: ChatMessage): Promise<boolean> {
    if (
      message.graphData &&
      Array.isArray(message.graphData.relationships) &&
      message.graphData.relationships.length > 0
    ) {
      return true;
    }

    if (message.graphUnavailable) {
      return false;
    }

    if (!message.id) {
      return false;
    }

    if (this.responseGraphLoadingMessageId === message.id) {
      return false;
    }

    this.responseGraphLoadingMessageId = message.id;
    this.responseGraphError = null;

    try {
      const graphResponse: any = await firstValueFrom(this.api.get(`/chat/messages/${message.id}/graph`));
      const rawGraph = graphResponse && typeof graphResponse === 'object' ? graphResponse : {};
      const entities = Array.isArray(rawGraph.entities) ? rawGraph.entities : [];
      const relationships = Array.isArray(rawGraph.relationships) ? rawGraph.relationships : [];
      const normalizedGraph = { ...rawGraph, entities, relationships };
      const hasData = relationships.length > 0;

      message.graphData = normalizedGraph;

      if (hasData) {
        message.graphUnavailable = false;
        return true;
      }

      message.graphUnavailable = true;
      this.responseGraphError = 'No relationships available for this answer yet.';
      console.warn(`No enriched graph relationships found for message ${message.id}`);
      return false;
    } catch (error) {
      console.error('Failed to load response graph:', error);
      this.responseGraphError = 'Failed to load graph details. Please try again.';
      return false;
    } finally {
      this.responseGraphLoadingMessageId = null;
    }
  }

  // Check if message has graph data to display
  hasGraphData(message: ChatMessage): boolean {
    if (message.role !== 'assistant') {
      return false;
    }
    if (message.graphUnavailable) {
      return false;
    }
    if (
      message.graphData &&
      Array.isArray(message.graphData.relationships) &&
      message.graphData.relationships.length > 0
    ) {
      return true;
    }
    const content = message.content || '';
    return /doc:[a-zA-Z0-9_]+/i.test(content);
  }

  // Open response graph in fullscreen modal
  async openResponseGraph(message: ChatMessage): Promise<void> {
    if (message.role !== 'assistant') {
      return;
    }

    const hasData = await this.ensureResponseGraphData(message);
    if (!hasData) {
      return;
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
    this.responseGraphError = null;
    this.responseGraphLoadingMessageId = null;
    
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

      // Clean up any existing tooltips
      ['response-node-tooltip', 'response-edge-tooltip'].forEach((id) => {
        const existing = document.getElementById(id);
        if (existing && existing.parentElement) {
          existing.parentElement.removeChild(existing);
        }
      });

      const MAX_NODE_TOOLTIP_PROPS = 5;

      // Add nodes (positions will be set by layout algorithm)
      entities.forEach((entity) => {
        const descriptionParts: string[] = [];
        const props = entity.properties || {};
        const entries = Object.entries(props)
          .filter(([key, value]) => value !== null && value !== undefined && String(value).trim() !== '');

        entries.slice(0, MAX_NODE_TOOLTIP_PROPS).forEach(([key, value]) => {
          let displayValue = value;
          if (typeof value === 'number' && Math.abs(value) >= 1000) {
            displayValue = new Intl.NumberFormat().format(value);
          }
          descriptionParts.push(`${this.formatLabel(key)}: ${displayValue}`);
        });

        const description = descriptionParts.join('\n');
        (this.responseGraphInstance as any).addNode(entity.id, {
          label: entity.name,
          x: 0,
          y: 0,
          size: 10,
          color: typeColors[entity.type] || '#94a3b8',
          description
        });
      });

      // Add edges
      const normalizedRelationships: Array<{
        key: string;
        from: string;
        to: string;
        label: string;
        properties: Record<string, any>;
      }> = [];
      const edgeDataByKey = new Map<string, any>();
      const MAX_EDGE_TOOLTIP_PROPS = 5;

      relationships.forEach((rel) => {
        const sourceId = rel.from_entity_id || rel.source || rel.from || rel.start || rel.head;
        const targetId = rel.to_entity_id || rel.target || rel.to || rel.end || rel.tail;
        if (!sourceId || !targetId) {
          return;
        }

        const type = rel.relationship_type || rel.type || rel.label || 'RELATED_TO';
        const relProps: Record<string, any> = { ...(rel.properties || {}) };

        if (rel.explanation && !relProps['explanation']) {
          relProps['explanation'] = rel.explanation;
        }
        if (rel.reasoning && !relProps['reasoning']) {
          relProps['reasoning'] = rel.reasoning;
        }
        if (rel.confidence !== undefined && relProps['confidence'] === undefined) {
          relProps['confidence'] = rel.confidence;
        }
        if (rel.impact && !relProps['impact']) {
          relProps['impact'] = rel.impact;
        }
        if (rel.source_description && !relProps['sourceDescription']) {
          relProps['sourceDescription'] = rel.source_description;
        }
        if (rel.citations && !relProps['citations']) {
          relProps['citations'] = rel.citations;
        }

        const edgeKey = `edge_${normalizedRelationships.length}`;
        normalizedRelationships.push({
          key: edgeKey,
          from: sourceId,
          to: targetId,
          label: type,
          properties: relProps
        });
        edgeDataByKey.set(edgeKey, {
          ...rel,
          relationship_type: type,
          from_entity_id: sourceId,
          to_entity_id: targetId,
          properties: relProps
        });
      });

      normalizedRelationships.forEach((rel) => {
        const hasSource = (this.responseGraphInstance as any).hasNode(rel.from);
        const hasTarget = (this.responseGraphInstance as any).hasNode(rel.to);

        if (hasSource && hasTarget) {
          const relProps = rel.properties || {};
          const relDescriptionParts: string[] = [];
          const relEntries = Object.entries(relProps)
            .filter(([key, value]) => value !== null && value !== undefined && String(value).trim() !== '');

          relEntries.slice(0, MAX_EDGE_TOOLTIP_PROPS).forEach(([key, value]) => {
            relDescriptionParts.push(`${this.formatLabel(key)}: ${value}`);
          });

          const relDescription = relDescriptionParts.join('\n');
          (this.responseGraphInstance as any).addEdgeWithKey(
            rel.key,
            rel.from,
            rel.to,
            {
              label: rel.label || 'RELATED_TO',
              size: 2,
              color: '#ef4444',
              type: 'arrow',
              description: relDescription
            }
          );
        }
      });

      // Apply layout to the response graph
      this.applyLayout(this.responseGraphInstance, this.responseGraphLayout);

      // Create Sigma instance
      const responseSigmaSettings = {
        // Node rendering
        renderLabels: true,
        labelSize: 10,
        labelWeight: 'normal',
        labelColor: { color: '#1f2937' },
        defaultNodeColor: '#10b981',
        minNodeSize: 5,
        maxNodeSize: 15,

        // Edge rendering
        renderEdgeLabels: true,
        edgeLabelSize: 10,
        edgeLabelColor: { color: '#6b7280' },
        edgeLabelWeight: 'normal',
        defaultEdgeColor: '#ef4444',
        defaultEdgeType: 'arrow',
        minEdgeSize: 1,
        maxEdgeSize: 4,

        // Interaction behaviour
        hideEdgesOnMove: false,
        hideLabelsOnMove: false,
        enableEdgeHoverEvents: true,
        enableEdgeClickEvents: true,
        enableEdgeEvents: true
      };

      this.responseSigmaInstance = new Sigma(
        this.responseGraphInstance,
        this.responseGraphContainer.nativeElement,
        responseSigmaSettings as any
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

        const attrs = (this.responseGraphInstance as any).getNodeAttributes(draggedNode);
        const description = attrs?.description;
        if (description) {
          let tooltip = document.getElementById('response-node-tooltip');
          if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'response-node-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = 'rgba(31, 41, 55, 0.95)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '12px';
            tooltip.style.maxWidth = '260px';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '10000';
            tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
            document.body.appendChild(tooltip);
          }
          tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
            <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
          `;
          tooltip.style.display = 'block';
          const updateTooltipPosition = (e: MouseEvent) => {
            if (tooltip) {
              tooltip.style.left = (e.clientX + 15) + 'px';
              tooltip.style.top = (e.clientY + 15) + 'px';
            }
          };
          container.addEventListener('mousemove', updateTooltipPosition);
          (tooltip as any)._removeListener = () => {
            container.removeEventListener('mousemove', updateTooltipPosition);
          };
        }
      });

      // Hover on node - show grab cursor
      this.responseSigmaInstance.on('enterNode', (event: any) => {
        container.style.cursor = 'grab';

        const nodeId = event.node;
        const attrs = (this.responseGraphInstance as any).getNodeAttributes(nodeId);
        const description = attrs?.description;
        if (description) {
          let tooltip = document.getElementById('response-node-tooltip');
          if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'response-node-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = 'rgba(31, 41, 55, 0.95)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '12px';
            tooltip.style.maxWidth = '260px';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '10000';
            tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
            document.body.appendChild(tooltip);
          }
          tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px">${attrs?.label || 'Entity'}</div>
            <div style="white-space:pre-wrap;color:#d1d5db;font-size:11px">${description}</div>
          `;
          tooltip.style.display = 'block';

          const updateTooltipPosition = (e: MouseEvent) => {
            if (tooltip) {
              tooltip.style.left = (e.clientX + 15) + 'px';
              tooltip.style.top = (e.clientY + 15) + 'px';
            }
          };
          container.addEventListener('mousemove', updateTooltipPosition);
          (tooltip as any)._removeListener = () => {
            container.removeEventListener('mousemove', updateTooltipPosition);
          };
        }
      });

      // Leave node - reset cursor
      this.responseSigmaInstance.on('leaveNode', () => {
        if (!isDragging) {
          container.style.cursor = 'default';
        }
        const tooltip = document.getElementById('response-node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
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
        const tooltip = document.getElementById('response-node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });

      // Mouse leave container - end drag
      this.responseSigmaInstance.getMouseCaptor().on('mouseleave', () => {
        if (draggedNode) {
          (this.responseGraphInstance as any).removeNodeAttribute(draggedNode, 'highlighted');
          draggedNode = null;
        }
        isDragging = false;
        container.style.cursor = 'default';
        const tooltip = document.getElementById('response-node-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });

      // Edge hover - show details tooltip
      this.responseSigmaInstance.on('enterEdge', (event: any) => {
        const edgeKey = event.edge;
        const edgeData = edgeDataByKey.get(edgeKey);
        if (!edgeData) {
          return;
        }

        const props = edgeData.properties || {};
        const explanation = props['reasoning'] || props['explanation'] || edgeData.explanation || 'No explanation provided';
        const impact = props['impact'] || props['effect'] || props['insight'];
        const confidenceValue = props['confidence'] ?? edgeData.confidence;
        const confidence = typeof confidenceValue === 'number'
          ? `${Math.round(confidenceValue * 100)}%`
          : (confidenceValue || null);
        const detectedBy = props['detected_by'] || props['source'] || edgeData.detected_by;

        let tooltip = document.getElementById('response-edge-tooltip');
        if (!tooltip) {
          tooltip = document.createElement('div');
          tooltip.id = 'response-edge-tooltip';
          tooltip.style.position = 'fixed';
          tooltip.style.backgroundColor = 'rgba(17, 24, 39, 0.95)';
          tooltip.style.color = 'white';
          tooltip.style.padding = '8px 12px';
          tooltip.style.borderRadius = '6px';
          tooltip.style.fontSize = '12px';
          tooltip.style.maxWidth = '320px';
          tooltip.style.pointerEvents = 'none';
          tooltip.style.zIndex = '10000';
          tooltip.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
          document.body.appendChild(tooltip);
        }

        const citationArray = props['citations'];
        const citationText = Array.isArray(citationArray) && citationArray.length > 0
          ? `<div style="color:#9ca3af;font-size:10px;margin-top:4px">Citation: ${citationArray[0]}</div>`
          : '';

        tooltip.innerHTML = `
          <div style="margin-bottom:4px;font-weight:600">${edgeData.relationship_type || 'RELATIONSHIP'}</div>
          <div style="color:#d1d5db;font-size:11px;white-space:pre-wrap">${explanation}</div>
          ${impact ? `<div style="color:#fbbf24;font-size:11px;margin-top:4px">Impact: ${impact}</div>` : ''}
          ${confidence ? `<div style="color:#34d399;font-size:10px;margin-top:4px">Confidence: ${confidence}</div>` : ''}
          ${detectedBy ? `<div style="color:#9ca3af;font-size:10px;margin-top:4px">Detected by: ${detectedBy}</div>` : ''}
          ${citationText}
        `;
        tooltip.style.display = 'block';

        const updateTooltipPosition = (e: MouseEvent) => {
          if (tooltip) {
            tooltip.style.left = (e.clientX + 15) + 'px';
            tooltip.style.top = (e.clientY + 15) + 'px';
          }
        };
        container.addEventListener('mousemove', updateTooltipPosition);
        (tooltip as any)._removeListener = () => {
          container.removeEventListener('mousemove', updateTooltipPosition);
        };
      });

      this.responseSigmaInstance.on('leaveEdge', () => {
        const tooltip = document.getElementById('response-edge-tooltip');
        if (tooltip) {
          tooltip.style.display = 'none';
          if ((tooltip as any)._removeListener) {
            (tooltip as any)._removeListener();
          }
        }
      });

      this.responseSigmaInstance.on('clickEdge', (event: any) => {
        const edgeKey = event.edge;
        const edgeData = edgeDataByKey.get(edgeKey);
        if (!edgeData) {
          return;
        }
        console.group('🔗 Response Relationship');
        console.log('Type:', edgeData.relationship_type || 'RELATIONSHIP');
        console.log('From:', edgeData.from_entity_id || edgeData.source || edgeData.from || edgeData.start);
        console.log('To:', edgeData.to_entity_id || edgeData.target || edgeData.to || edgeData.end);
        console.log('Properties:', edgeData.properties);
        console.groupEnd();
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

