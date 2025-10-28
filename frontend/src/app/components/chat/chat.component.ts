import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-4xl mx-auto">
      <div class="card">
        <h2 class="text-2xl font-bold text-gray-900 mb-2">
          💬 AI Financial Assistant
        </h2>
        <p class="text-gray-600 mb-6">
          Ask questions about your financial documents and get evidence-backed insights.
        </p>

        <!-- Chat Messages -->
        <div class="bg-gray-50 rounded-lg p-4 h-96 overflow-y-auto mb-4 scrollbar-thin">
          <div class="space-y-4">
            <!-- Assistant Message -->
            <div class="flex items-start space-x-3">
              <div class="bg-primary-600 h-8 w-8 rounded-full flex items-center justify-center text-white">
                AI
              </div>
              <div class="flex-1 bg-white rounded-lg p-3 shadow-sm">
                <p class="text-sm text-gray-800">
                  Hello! I'm ArthaNethra, your AI financial investigation assistant. 
                  Upload a document and ask me questions about risks, entities, or relationships.
                </p>
              </div>
            </div>

            <!-- User Message Example -->
            <div class="flex items-start space-x-3 justify-end">
              <div class="flex-1 bg-primary-100 rounded-lg p-3 max-w-md ml-auto">
                <p class="text-sm text-gray-800">
                  What are the high-risk variable-rate debts?
                </p>
              </div>
              <div class="bg-gray-600 h-8 w-8 rounded-full flex items-center justify-center text-white">
                U
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="flex space-x-3">
          <input 
            type="text" 
            [(ngModel)]="userMessage"
            (keyup.enter)="sendMessage()"
            placeholder="Ask a question..." 
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500">
          <button 
            (click)="sendMessage()"
            class="btn btn-primary">
            Send
          </button>
        </div>

        <!-- Example Queries -->
        <div class="mt-4">
          <p class="text-sm text-gray-600 mb-2">Example queries:</p>
          <div class="flex flex-wrap gap-2">
            <button class="text-xs px-3 py-1 bg-gray-100 rounded-full hover:bg-gray-200">
              Show all variable-rate debt
            </button>
            <button class="text-xs px-3 py-1 bg-gray-100 rounded-full hover:bg-gray-200">
              What are the biggest risks?
            </button>
            <button class="text-xs px-3 py-1 bg-gray-100 rounded-full hover:bg-gray-200">
              List all subsidiaries
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ChatComponent {
  userMessage = '';

  sendMessage() {
    console.log('Sending message:', this.userMessage);
    this.userMessage = '';
  }
}

