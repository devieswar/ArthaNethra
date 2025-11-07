import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, Pipe, PipeTransform, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml, SafeResourceUrl } from '@angular/platform-browser';
import { EChartsOption } from 'echarts';
import Graph from 'graphology';
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
  template: `
    <div class="h-screen flex flex-col bg-gray-50">
      
      <!-- Header with Branding -->
      <header class="bg-white shadow-sm border-b border-gray-200">
        <div class="px-6 py-4">
          <div class="flex items-center space-x-3">
            <div class="h-10 w-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center shadow-md">
              <span class="text-white font-bold text-xl">AN</span>
            </div>
            <div>
              <h1 class="text-2xl font-bold text-gray-900">ArthaNethra</h1>
              <p class="text-xs text-gray-500">AI Financial Risk Investigator</p>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Content Area -->
      <div class="flex-1 flex overflow-hidden">
      
      <!-- Left Sidebar: Chat Sessions -->
      <div class="w-72 bg-gradient-to-b from-gray-50 to-white border-r border-gray-200 flex flex-col shadow-sm">
        <div class="p-4 border-b border-gray-200 bg-white">
          <button 
            (click)="createNewSession()"
            class="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white px-4 py-2.5 rounded-xl hover:shadow-lg hover:scale-[1.02] transition-all duration-200 flex items-center justify-center gap-2 font-medium shadow-md">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
            </svg>
            New Chat
          </button>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <div *ngFor="let session of sessions" 
               [class.bg-gradient-to-r]="currentSession?.id === session.id"
               [class.from-primary-50]="currentSession?.id === session.id"
               [class.to-primary-100]="currentSession?.id === session.id"
               [class.border-l-4]="currentSession?.id === session.id"
               [class.border-primary-600]="currentSession?.id === session.id"
               [class.shadow-sm]="currentSession?.id === session.id"
               class="px-3 py-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-all duration-150 group relative">
            <div class="flex items-start justify-between" (click)="selectSession(session)">
              <div class="flex-1 min-w-0 pr-2">
                <!-- Chat Icon Avatar -->
                <div class="flex items-center gap-2 mb-2">
                  <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                    </svg>
                  </div>
                  <!-- Editable Name -->
                  <div class="flex-1 min-w-0">
                    <input 
                      *ngIf="session.isEditing"
                      [(ngModel)]="session.name"
                      (blur)="saveSessionName(session)"
                      (keydown.enter)="saveSessionName(session)"
                      (keydown.escape)="cancelEditSessionName(session)"
                      (click)="$event.stopPropagation()"
                      class="w-full px-2 py-1 text-sm font-medium text-gray-900 border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                      [attr.aria-label]="'Edit chat name'" />
                    <p *ngIf="!session.isEditing" class="font-medium text-sm text-gray-900 truncate">{{ session.name }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-500 ml-10">
                  <span class="flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    {{ session.document_ids.length }} docs
                  </span>
                  <span class="flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                    </svg>
                    {{ session.message_count || 0 }} msgs
                  </span>
                </div>
              </div>
              <!-- Action Buttons (show on hover) -->
              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                <button 
                  (click)="startEditSessionName(session, $event)"
                  class="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                  title="Edit name">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                  </svg>
                </button>
                <button 
                  (click)="deleteSession(session.id, $event)"
                  class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Delete chat">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <div *ngIf="sessions.length === 0" class="p-8 text-center">
            <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
            </svg>
            <p class="text-gray-500 text-sm font-medium">No chats yet</p>
            <p class="text-gray-400 text-xs mt-1">Create one to get started!</p>
          </div>
        </div>
      </div>

      <!-- Center: Chat Messages + Document Management -->
      <div class="flex-1 flex flex-col">
        
        <!-- Header -->
        <div class="bg-white border-b border-gray-200 px-6 py-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-xl font-semibold text-gray-900">
                {{ currentSession?.name || 'Select a chat' }}
              </h2>
              <p class="text-sm text-gray-500 mt-1" *ngIf="currentSession">
                {{ messages.length }} messages • {{ currentSession.document_ids.length }} documents
              </p>
            </div>
            
            <div class="flex items-center gap-2">
              <!-- Upload Document -->
              <label class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                Upload Document
                <input type="file" (change)="uploadDocument($event)" class="hidden" accept=".pdf,.zip" />
              </label>
              
              <!-- Add Existing Documents -->
              <button 
                *ngIf="availableDocuments.length > 0"
                (click)="showAvailableDocuments = true"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                </svg>
                Add Existing ({{ availableDocuments.length }})
              </button>
              
              <!-- Toggle Explorer -->
              <button 
                (click)="showExplorer = !showExplorer"
                class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Explorer
              </button>
            </div>
          </div>
          
          <!-- Documents Chips -->
          <div *ngIf="currentSession && currentDocuments.length > 0" class="flex flex-wrap gap-2 mt-3">
            <div *ngFor="let doc of currentDocuments" 
                 class="flex items-center gap-2 bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm border border-blue-200">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <span>{{ doc.filename }}</span>
              <span class="text-xs">({{ doc.entities_count }} entities)</span>
              <button 
                (click)="removeDocumentFromSession(doc.id)"
                class="hover:text-red-600">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <div #chatMessages class="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-50 to-white custom-scrollbar">
          <div *ngIf="!currentSession" class="h-full flex items-center justify-center text-gray-400">
            <div class="text-center">
              <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl flex items-center justify-center shadow-lg">
                <svg class="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                </svg>
              </div>
              <p class="text-lg font-medium text-gray-700">Select or create a chat to get started</p>
              <p class="text-sm text-gray-500 mt-2">Upload documents and start asking questions</p>
            </div>
          </div>

          <!-- User Message -->
          <div *ngFor="let msg of messages" class="flex gap-3 animate-fadeIn"
               [class.flex-row-reverse]="msg.role === 'user'">
            <!-- Avatar -->
            <div class="flex-shrink-0">
              <div *ngIf="msg.role === 'user'" 
                   class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white font-bold shadow-md">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                </svg>
              </div>
              <div *ngIf="msg.role === 'assistant'" 
                   class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold shadow-md">
                <span class="text-sm">AI</span>
              </div>
            </div>
            
            <!-- Message Content -->
            <div class="flex-1 max-w-3xl">
              <div [class.bg-gradient-to-r]="msg.role === 'user'"
                   [class.from-primary-600]="msg.role === 'user'"
                   [class.to-primary-700]="msg.role === 'user'"
                   [class.text-white]="msg.role === 'user'"
                   [class.ml-auto]="msg.role === 'user'"
                   [class.bg-white]="msg.role === 'assistant'"
                   [class.shadow-md]="msg.role === 'assistant'"
                   [class.border]="msg.role === 'assistant'"
                   [class.border-gray-200]="msg.role === 'assistant'"
                   class="px-5 py-4 rounded-2xl transition-all duration-200 hover:shadow-lg">
                <!-- Role Label -->
                <div class="flex items-center gap-2 mb-2">
                  <span class="text-xs font-semibold uppercase tracking-wider"
                        [class.text-white]="msg.role === 'user'"
                        [class.text-gray-500]="msg.role === 'assistant'">
                    {{ msg.role === 'user' ? 'You' : 'ArthaNethra AI' }}
                  </span>
                </div>
                
                <!-- Message Text with Markdown Support -->
                <div class="prose prose-sm max-w-none"
                     [class.prose-invert]="msg.role === 'user'"
                     [innerHTML]="renderMarkdown(msg.content)">
                </div>
                
                <!-- Timestamp -->
                <p class="text-xs mt-3 opacity-70 flex items-center gap-1"
                   [class.text-white]="msg.role === 'user'"
                   [class.text-gray-500]="msg.role === 'assistant'">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  {{ formatTime(msg.created_at) }}
                </p>
              </div>
            </div>
          </div>

          <!-- Loading Animation -->
          <div *ngIf="isLoading" class="flex gap-3 animate-fadeIn">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold shadow-md">
              <span class="text-sm">AI</span>
            </div>
            <div class="bg-white shadow-md border border-gray-200 px-5 py-4 rounded-2xl">
              <div class="flex items-center gap-2">
                <div class="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-bounce"></div>
                <div class="w-2.5 h-2.5 bg-teal-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                <div class="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                <span class="ml-2 text-sm text-gray-500">Thinking...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="bg-white border-t border-gray-200 p-6 shadow-lg">
          <div class="max-w-4xl mx-auto">
            <div class="flex gap-3 items-end">
              <div class="flex-1 relative">
                <textarea 
                  [(ngModel)]="userMessage"
                  (keydown)="handleKeyDown($event)"
                  [disabled]="!currentSession || isLoading"
                  placeholder="Ask about your financial documents... (Shift+Enter for new line)"
                  rows="1"
                  class="w-full px-5 py-4 border-2 border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 resize-none shadow-sm transition-all duration-200 hover:border-primary-300"
                  style="min-height: 56px; max-height: 200px;"></textarea>
                <div class="absolute right-4 bottom-4 flex items-center gap-2 text-xs text-gray-400">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                  <span>{{ !currentSession ? 'Select a chat first' : isLoading ? 'AI is thinking...' : 'Enter to send' }}</span>
                </div>
              </div>
              <button 
                (click)="sendMessage()"
                [disabled]="!currentSession || isLoading || !userMessage.trim()"
                class="px-6 py-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-2xl hover:shadow-xl hover:scale-105 disabled:bg-gray-300 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200 flex items-center justify-center gap-2 font-medium shadow-lg">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
                </svg>
                <span class="hidden sm:inline">Send</span>
              </button>
            </div>
            <div *ngIf="currentSession" class="mt-3 text-xs text-gray-500 flex items-center justify-center gap-2">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>AI-powered financial analysis • {{ currentDocuments.length }} document{{ currentDocuments.length !== 1 ? 's' : '' }} active</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Document Explorer -->
      <div *ngIf="showExplorer" class="w-96 bg-white border-l border-gray-200 flex flex-col">
        <div class="p-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 class="font-semibold text-gray-900">Document Explorer</h3>
            <p class="text-xs text-gray-500 mt-1">View data & relationships</p>
          </div>
          <button (click)="showExplorer = false" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="flex-1 overflow-y-auto p-4">
          
          <!-- Back Button (when viewing specific document) -->
          <button *ngIf="explorerView !== 'list'" 
                  (click)="explorerView = 'list'; selectedDocument = null"
                  class="mb-4 flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            Back to documents
          </button>

          <!-- Document List View -->
          <div *ngIf="explorerView === 'list'">
            <div *ngIf="currentDocuments.length === 0" class="text-center text-gray-500 text-sm py-8">
              No documents in this chat yet
            </div>
            
            <div *ngFor="let doc of currentDocuments" class="mb-4 border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
            <div class="bg-gray-50 px-3 py-2 border-b border-gray-200">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-sm text-gray-900 truncate">{{ doc.filename }}</p>
                  <div class="flex gap-3 text-xs text-gray-500 mt-1">
                    <span>{{ doc.entities_count }} entities</span>
                    <span>{{ doc.edges_count }} relationships</span>
                  </div>
                </div>
                <button 
                  (click)="confirmDeleteDocument(doc, $event)"
                  class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Delete document">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                  </svg>
                </button>
              </div>
            </div>
            
            <div class="p-3 space-y-1">
              <button 
                (click)="viewDocumentGraph(doc)"
                [disabled]="!doc.graph_id"
                [class.opacity-50]="!doc.graph_id"
                [class.cursor-not-allowed]="!doc.graph_id"
                class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 rounded flex items-center gap-2 disabled:hover:bg-transparent">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
                </svg>
                <span class="font-medium">Knowledge Graph</span>
              </button>
              <button 
                (click)="viewDocumentEntities(doc)"
                [disabled]="!doc.graph_id"
                [class.opacity-50]="!doc.graph_id"
                [class.cursor-not-allowed]="!doc.graph_id"
                class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 rounded flex items-center gap-2 disabled:hover:bg-transparent">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path>
                </svg>
                Entities ({{ doc.entities_count || 0 }})
              </button>
              <button 
                (click)="viewDocumentRisks(doc)"
                [disabled]="!doc.graph_id"
                [class.opacity-50]="!doc.graph_id"
                [class.cursor-not-allowed]="!doc.graph_id"
                class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 rounded flex items-center gap-2 disabled:hover:bg-transparent">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
                Risk Analysis
              </button>
              <button 
                (click)="viewDocumentPDF(doc)"
                class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 rounded flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                </svg>
                View PDF
              </button>
              <button 
                (click)="viewDocumentMarkdown(doc)"
                class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 rounded flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Markdown
              </button>
            </div>
          </div>
          </div>
          
          <!-- Graph View -->
          <div *ngIf="explorerView === 'graph'" class="h-full flex flex-col">
            <div class="mb-4">
              <h4 class="font-semibold text-gray-900">{{ selectedDocument?.filename }}</h4>
              <p class="text-sm text-gray-500">Interactive Knowledge Graph</p>
            </div>
            
            <div *ngIf="graphEntities.length === 0" class="text-center text-gray-500 py-8">
              <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
              <p>No entities found</p>
            </div>
            
            <div *ngIf="graphEntities.length > 0" class="flex-1 flex flex-col">
              <!-- Graph Stats -->
              <div class="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-semibold text-blue-900">Interactive Graph</div>
                    <div class="text-xs text-blue-700 mt-1">{{ graphEntities.length }} nodes • {{ graphEdges.length }} edges</div>
                  </div>
                  <div class="flex items-center gap-3">
                    <div class="text-xs text-blue-600">
                      <span class="block">Drag to pan</span>
                      <span class="block">Scroll to zoom</span>
                    </div>
                    <button 
                      (click)="openGraphFullscreen()"
                      class="p-2 hover:bg-blue-100 rounded-lg transition-colors group"
                      title="Open fullscreen">
                      <svg class="w-5 h-5 text-blue-600 group-hover:text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
              
              <!-- Sigma Graph Container -->
              <div #sigmaContainer class="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden" style="min-height: 400px;"></div>
            </div>
          </div>
          
          <!-- Entities List View -->
          <div *ngIf="explorerView === 'entities'" class="h-full flex flex-col">
            <div class="mb-4">
              <h4 class="font-semibold text-gray-900">{{ selectedDocument?.filename }}</h4>
              <p class="text-sm text-gray-500">Entities ({{ graphEntities.length }})</p>
            </div>
            
            <div *ngIf="graphEntities.length === 0" class="text-center text-gray-500 py-8">
              <p>No entities extracted yet</p>
            </div>
            
            <div *ngIf="graphEntities.length > 0" class="flex-1 overflow-y-auto space-y-2">
              <div *ngFor="let entity of graphEntities" class="p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <div class="flex items-start justify-between mb-2">
                  <div class="font-semibold text-sm">{{ entity.name }}</div>
                  <span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">{{ entity.type }}</span>
                </div>
                <div *ngIf="entity.properties" class="text-xs text-gray-600 space-y-1">
                  <div *ngFor="let key of objectKeys(entity.properties).slice(0, 5)" class="flex gap-2">
                    <span class="font-medium text-gray-700">{{ key }}:</span>
                    <span class="truncate">{{ entity.properties[key] }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Markdown View -->
          <div *ngIf="explorerView === 'markdown'" class="h-full flex flex-col">
            <div class="mb-4">
              <h4 class="font-semibold text-gray-900">{{ selectedDocument?.filename }}</h4>
              <p class="text-sm text-gray-500">Extracted Content</p>
            </div>
            
            <div class="flex items-center justify-between mb-2">
              <div class="text-xs text-gray-500">Rendered Markdown</div>
              <button (click)="openMarkdownFullscreen()"
                      class="px-2 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-100"
                      title="Open fullscreen">
                Expand
              </button>
            </div>

            <div class="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 prose prose-sm max-w-none">
              <div *ngIf="!markdownHtml" class="text-center text-gray-500 py-8">
                <p>No markdown content available</p>
              </div>
              <div *ngIf="markdownHtml" [innerHTML]="markdownHtml"></div>
            </div>
          </div>
          
          <!-- Risk Analysis View -->
          <div *ngIf="explorerView === 'risks'" class="h-full flex flex-col">
            <div class="flex-1 overflow-y-auto">
              <div class="space-y-4 pb-4">
                <div class="px-0">
                  <div class="mb-1">
                    <h4 class="font-semibold text-gray-900">{{ selectedDocument?.filename }}</h4>
                    <p class="text-sm text-gray-500">Risk Analysis</p>
                  </div>
                </div>

                <!-- Risk Chart -->
                <div *ngIf="riskSummary" class="bg-white rounded-lg border border-gray-200 p-4">
                  <h5 class="text-sm font-semibold text-gray-900 mb-3">Risk Distribution</h5>
                  <div echarts [options]="riskChartOptions" class="h-48"></div>
                </div>

                <div *ngIf="riskSummary" class="grid grid-cols-2 gap-2">
                  <div class="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div class="text-xs text-red-600">Critical</div>
                    <div class="text-2xl font-bold text-red-700">{{ riskSummary.critical_severity || 0 }}</div>
                  </div>
                  <div class="bg-orange-50 border border-orange-200 rounded-lg p-3">
                    <div class="text-xs text-orange-600">High</div>
                    <div class="text-2xl font-bold text-orange-700">{{ riskSummary.high_severity || 0 }}</div>
                  </div>
                  <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <div class="text-xs text-yellow-600">Medium</div>
                    <div class="text-2xl font-bold text-yellow-700">{{ riskSummary.medium_severity || 0 }}</div>
                  </div>
                  <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div class="text-xs text-blue-600">Low</div>
                    <div class="text-2xl font-bold text-blue-700">{{ riskSummary.low_severity || 0 }}</div>
                  </div>
                </div>

                <div class="space-y-3">
                  <div *ngIf="documentRisks.length === 0" class="text-center text-gray-500 text-sm py-8">
                    No risks detected
                  </div>

                  <div *ngFor="let risk of documentRisks"
                       class="border rounded-lg p-3"
                       [class.border-red-300]="risk.severity === 'critical'"
                       [class.bg-red-50]="risk.severity === 'critical'"
                       [class.border-orange-300]="risk.severity === 'high'"
                       [class.bg-orange-50]="risk.severity === 'high'"
                       [class.border-yellow-300]="risk.severity === 'medium'"
                       [class.bg-yellow-50]="risk.severity === 'medium'"
                       [class.border-blue-300]="risk.severity === 'low'"
                       [class.bg-blue-50]="risk.severity === 'low'">
                    <div class="flex items-start justify-between mb-2">
                      <h5 class="font-semibold text-sm">{{ risk.type }}</h5>
                      <span class="text-xs px-2 py-1 rounded uppercase font-semibold"
                            [class.bg-red-200]="risk.severity === 'critical'"
                            [class.text-red-800]="risk.severity === 'critical'"
                            [class.bg-orange-200]="risk.severity === 'high'"
                            [class.text-orange-800]="risk.severity === 'high'"
                            [class.bg-yellow-200]="risk.severity === 'medium'"
                            [class.text-yellow-800]="risk.severity === 'medium'"
                            [class.bg-blue-200]="risk.severity === 'low'"
                            [class.text-blue-800]="risk.severity === 'low'">
                        {{ risk.severity }}
                      </span>
                    </div>
                    <p class="text-sm text-gray-700 mb-2">{{ risk.description }}</p>
                    <p class="text-xs text-gray-600 mb-2"><strong>Recommendation:</strong> {{ risk.recommendation }}</p>
                    <div class="text-xs text-gray-500">
                      <span>Score: {{ (risk.score * 100).toFixed(0) }}%</span>
                      <span class="mx-2">•</span>
                      <span *ngIf="risk.citations && risk.citations.length > 0">
                        Citations: Page {{ risk.citations[0].page }}
                        <span *ngIf="risk.citations[0].section">, {{ risk.citations[0].section }}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- PDF Viewer -->
          <div *ngIf="explorerView === 'pdf'" class="h-full flex flex-col">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <h4 class="font-semibold text-gray-900">{{ selectedDocument?.filename }}</h4>
                <p class="text-sm text-gray-500">Original Document</p>
              </div>
              <a [href]="'http://localhost:8000/api/v1/documents/' + selectedDocument?.id + '/pdf'" 
                 target="_blank"
                 class="px-3 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                </svg>
                Open in Tab
              </a>
            </div>
            
            <div class="flex-1 bg-gray-100 rounded-lg overflow-hidden">
              <ngx-extended-pdf-viewer
                *ngIf="selectedDocument && selectedDocument.id"
                [src]="'http://localhost:8000/api/v1/documents/' + selectedDocument.id + '/pdf'"
                [height]="'100%'"
                [showToolbar]="true"
                [showSidebarButton]="true"
                [showFindButton]="true"
                [showPagingButtons]="true"
                [showZoomButtons]="true"
                [showPresentationModeButton]="false"
                [showOpenFileButton]="false"
                [showPrintButton]="true"
                [showDownloadButton]="true"
                [showSecondaryToolbarButton]="true"
                [showRotateButton]="false"
                [showHandToolButton]="true"
                [showScrollingButton]="true"
                [showSpreadButton]="true"
                [showPropertiesButton]="true"
                [textLayer]="true"
                [zoom]="'auto'"
                backgroundColor="#f3f4f6">
              </ngx-extended-pdf-viewer>
            </div>
          </div>
          
        </div>
      </div>
      
      </div><!-- End Main Content Area -->

      <!-- Available Documents Modal -->
      <div *ngIf="showAvailableDocuments" 
           class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fadeIn"
           (click)="showAvailableDocuments = false">
        <div class="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col animate-fadeIn" (click)="$event.stopPropagation()">
          <!-- Header -->
          <div class="bg-gradient-to-r from-emerald-600 to-teal-700 text-white px-6 py-5 rounded-t-2xl flex items-center justify-between shadow-lg">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-white bg-opacity-20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
              </div>
              <div>
                <h3 class="text-xl font-bold">Add Existing Documents</h3>
                <p class="text-emerald-100 text-sm mt-0.5">{{ availableDocuments.length }} document{{ availableDocuments.length !== 1 ? 's' : '' }} available</p>
              </div>
            </div>
            <button (click)="showAvailableDocuments = false" 
                    class="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
                    title="Close">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          
          <!-- Content -->
          <div class="flex-1 overflow-hidden flex flex-col">
            <!-- Search Bar -->
            <div class="px-6 pt-6 pb-4">
              <div class="relative">
                <svg class="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
                <input 
                  [(ngModel)]="documentSearchQuery"
                  (ngModelChange)="filterAvailableDocuments()"
                  type="text" 
                  placeholder="Search documents by name..."
                  class="w-full pl-12 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all">
                <button 
                  *ngIf="documentSearchQuery"
                  (click)="documentSearchQuery = ''; filterAvailableDocuments()"
                  class="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Document List -->
            <div class="flex-1 overflow-y-auto px-6 pb-6 custom-scrollbar">
              <!-- Empty State -->
              <div *ngIf="filteredAvailableDocuments.length === 0" class="text-center py-12">
                <div class="w-20 h-20 mx-auto mb-4 bg-gray-100 rounded-2xl flex items-center justify-center">
                  <svg class="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <p class="text-gray-500 font-medium">{{ documentSearchQuery ? 'No documents match your search' : 'No documents available to add' }}</p>
                <p class="text-gray-400 text-sm mt-1">{{ documentSearchQuery ? 'Try a different search term' : 'Upload new documents to get started' }}</p>
              </div>
              
              <!-- Document Cards -->
              <div class="space-y-3">
                <div *ngFor="let doc of filteredAvailableDocuments" 
                     class="group border-2 border-gray-200 rounded-xl p-4 hover:border-emerald-300 hover:shadow-md transition-all duration-200 bg-white">
                  <div class="flex items-start gap-4">
                    <!-- Document Icon -->
                    <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                      <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                    </div>
                    
                    <!-- Document Info -->
                    <div class="flex-1 min-w-0">
                      <h4 class="font-semibold text-gray-900 truncate group-hover:text-emerald-700 transition-colors">{{ doc.filename }}</h4>
                      <div class="flex flex-wrap items-center gap-4 mt-2">
                        <span class="flex items-center gap-1.5 text-sm text-gray-600">
                          <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                          </svg>
                          <strong class="text-gray-900">{{ doc.entities_count || 0 }}</strong> entities
                        </span>
                        <span class="flex items-center gap-1.5 text-sm text-gray-600">
                          <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                          </svg>
                          <strong class="text-gray-900">{{ doc.edges_count || 0 }}</strong> relationships
                        </span>
                        <span *ngIf="doc.status === 'indexed'" class="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-semibold flex items-center gap-1">
                          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                          </svg>
                          Ready
                        </span>
                      </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex flex-col items-stretch gap-2">
                      <button 
                        (click)="addExistingDocument(doc)"
                        class="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-700 text-white rounded-xl hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center gap-2 font-medium whitespace-nowrap">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                        </svg>
                        Add to Chat
                      </button>
                      <button
                        (click)="confirmDeleteDocument(doc, $event)"
                        class="px-5 py-2.5 border-2 border-red-200 text-red-600 rounded-xl hover:bg-red-50 hover:border-red-300 transition-all duration-200 flex items-center gap-2 font-medium whitespace-nowrap"
                        title="Delete document permanently">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Footer -->
          <div class="px-6 py-4 bg-gray-50 rounded-b-2xl border-t border-gray-200">
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-600">
                Select documents to enhance your chat session
              </span>
              <button 
                (click)="showAvailableDocuments = false"
                class="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors font-medium">
                Close
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Progress Modal (outside overflow container for proper z-index) -->
      <div *ngIf="showProgressModal" 
           class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
          <div class="bg-primary-600 text-white px-6 py-4 rounded-t-lg">
            <h3 class="text-lg font-semibold">Processing Document</h3>
            <p class="text-primary-100 text-sm" *ngIf="uploadingFile">{{ uploadingFile.name }}</p>
          </div>
          
          <div class="p-6">
            <div class="space-y-3">
              <div *ngFor="let step of progressSteps" 
                   class="flex items-center space-x-3"
                   [class.opacity-40]="step.status === 'pending'">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 rounded-full flex items-center justify-center"
                       [class.bg-gray-200]="step.status === 'pending'"
                       [class.bg-primary-600]="step.status === 'active'"
                       [class.bg-green-500]="step.status === 'completed'"
                       [class.bg-red-500]="step.status === 'error'">
                    <svg *ngIf="step.status === 'completed'" 
                         class="w-5 h-5 text-white" 
                         fill="none" 
                         stroke="currentColor" 
                         viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <div *ngIf="step.status === 'active'" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <div *ngIf="step.status === 'pending'" class="w-2 h-2 bg-gray-400 rounded-full"></div>
                  </div>
                </div>
                <div class="flex-1">
                  <p class="text-sm font-medium"
                     [class.text-gray-400]="step.status === 'pending'"
                     [class.text-gray-900]="step.status === 'active'"
                     [class.text-gray-500]="step.status === 'completed'">
                    {{ step.label }}
                  </p>
                </div>
              </div>
            </div>
            
            <div class="mt-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm text-gray-600">Progress</span>
                <span class="text-sm font-semibold">{{ getProgress() }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-primary-600 h-2 rounded-full transition-all duration-300"
                     [style.width.%]="getProgress()"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Fullscreen Graph Modal -->
      <div *ngIf="isGraphFullscreen" 
           class="fixed inset-0 z-50 bg-white flex items-center justify-center">
        <div class="w-full h-full flex flex-col">
          <!-- Fullscreen Header -->
          <div class="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 shadow-sm">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ selectedDocument?.filename }}</h3>
              <p class="text-sm text-gray-600">{{ graphEntities.length }} nodes • {{ graphEdges.length }} edges</p>
            </div>
            <div class="flex items-center gap-4">
              <div class="text-xs text-gray-600">
                <span class="block">🖱️ Drag nodes to reposition</span>
                <span class="block">↔️ Pan: Drag background • 🔍 Zoom: Mouse wheel</span>
              </div>
              <button 
                (click)="closeGraphFullscreen()"
                class="p-2 hover:bg-white hover:shadow-md rounded-lg transition-all group"
                title="Close fullscreen">
                <svg class="w-6 h-6 text-gray-600 group-hover:text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
          
          <!-- Fullscreen Graph Container -->
          <div #sigmaContainerFullscreen class="flex-1 bg-white" style="width: 100%; height: calc(100vh - 73px);"></div>
        </div>
      </div>

      <!-- Fullscreen Markdown Modal -->
      <div *ngIf="isMarkdownFullscreen"
           class="fixed inset-0 z-50 bg-white flex flex-col">
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">{{ selectedDocument?.filename }}</h3>
            <p class="text-sm text-gray-500">Rendered Markdown</p>
          </div>
          <div class="flex items-center gap-2">
            <button (click)="closeMarkdownFullscreen()"
                    class="p-2 rounded-full hover:bg-gray-100"
                    title="Close fullscreen">
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto bg-gray-50 p-6">
          <div class="prose prose-sm md:prose lg:prose-lg max-w-none" [innerHTML]="markdownHtml"></div>
        </div>
      </div>

      <!-- Delete Document Confirmation Dialog -->
      <div *ngIf="showDeleteConfirm"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full animate-fadeIn">
          <!-- Header -->
          <div class="p-6 border-b border-gray-200">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-gray-900">Delete Document?</h3>
                <p class="text-sm text-gray-500 mt-1">This action cannot be undone</p>
              </div>
            </div>
          </div>
          
          <!-- Content -->
          <div class="p-6">
            <p class="text-sm text-gray-600">
              Are you sure you want to delete <span class="font-semibold text-gray-900">{{ documentToDelete?.filename }}</span>?
            </p>
            <div class="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
              <p class="text-xs text-red-800">
                <strong>Warning:</strong> This will permanently delete:
              </p>
              <ul class="text-xs text-red-700 mt-2 space-y-1 ml-4">
                <li>• The uploaded file</li>
                <li>• All extracted entities ({{ documentToDelete?.entities_count || 0 }})</li>
                <li>• All relationships ({{ documentToDelete?.edges_count || 0 }})</li>
                <li>• The knowledge graph data</li>
              </ul>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="p-6 border-t border-gray-200 flex items-center justify-end gap-3">
            <button 
              (click)="cancelDeleteDocument()"
              [disabled]="isDeleting"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50">
              Cancel
            </button>
            <button 
              (click)="deleteDocument()"
              [disabled]="isDeleting"
              class="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-red-600 to-red-700 rounded-lg hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2">
              <svg *ngIf="isDeleting" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              <span>{{ isDeleting ? 'Deleting...' : 'Delete Document' }}</span>
            </button>
          </div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100vh;
    }
    
    /* Custom Scrollbar */
    .custom-scrollbar::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #f1f5f9;
      border-radius: 4px;
    }
    
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
      transition: background 0.2s;
    }
    
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }
    
    /* Fade In Animation */
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .animate-fadeIn {
      animation: fadeIn 0.3s ease-out;
    }
    
    /* Markdown Prose Styling for Messages */
    .prose {
      max-width: none;
    }
    
    .prose h1, .prose h2, .prose h3 {
      margin-top: 1em;
      margin-bottom: 0.5em;
      font-weight: 600;
    }
    
    .prose ul, .prose ol {
      margin-top: 0.5em;
      margin-bottom: 0.5em;
      padding-left: 1.5em;
    }
    
    .prose li {
      margin-top: 0.25em;
      margin-bottom: 0.25em;
    }
    
    .prose code {
      background-color: rgba(0, 0, 0, 0.05);
      padding: 0.125rem 0.25rem;
      border-radius: 0.25rem;
      font-size: 0.875em;
    }
    
    .prose pre {
      background-color: #1e293b;
      color: #e2e8f0;
      padding: 1rem;
      border-radius: 0.5rem;
      overflow-x: auto;
      margin-top: 0.75em;
      margin-bottom: 0.75em;
    }
    
    .prose pre code {
      background-color: transparent;
      color: inherit;
      padding: 0;
    }
    
    .prose-invert code {
      background-color: rgba(255, 255, 255, 0.1);
    }
    
    .prose-invert pre {
      background-color: rgba(0, 0, 0, 0.2);
    }
    
    .prose strong {
      font-weight: 600;
    }
    
    .prose a {
      color: #3b82f6;
      text-decoration: underline;
    }
    
    .prose-invert a {
      color: #93c5fd;
    }
    
    /* Textarea auto-resize */
    textarea {
      field-sizing: content;
    }
  `]
})
export class ChatUnifiedComponent implements OnInit, OnDestroy {
  @ViewChild('chatMessages') chatMessages!: ElementRef;
  @ViewChild('sigmaContainer') sigmaContainer!: ElementRef;
  @ViewChild('sigmaContainerFullscreen') sigmaContainerFullscreen!: ElementRef;

  sessions: ChatSession[] = [];
  currentSession: ChatSession | null = null;
  messages: ChatMessage[] = [];
  userMessage = '';
  isLoading = false;
  isGraphFullscreen = false;
  
  // Sigma graph
  private sigmaInstance: Sigma | null = null;
  private graphInstance: any = null;
  
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

  constructor(private api: ApiService, private sanitizer: DomSanitizer) {}

  async ngOnInit() {
    await this.loadSessions();
    await this.loadDocuments();
    
    // Create default session if none exist
    if (this.sessions.length === 0) {
      await this.createNewSession();
    }
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
    this.availableDocuments = this.allDocuments.filter(
      doc => !this.currentSession!.document_ids.includes(doc.id) && doc.status === 'indexed'
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
      
      // Add nodes with random spread layout (better for force-directed feel)
      console.log('🔵 Adding nodes to graph...');
      this.graphEntities.forEach((entity, index) => {
        // Spread nodes randomly across a large area
        const x = (Math.random() - 0.5) * 200; // -100 to 100
        const y = (Math.random() - 0.5) * 200; // -100 to 100
        
        (this.graphInstance as any).addNode(entity.id, {
          label: entity.name,
          x: x,
          y: y,
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

