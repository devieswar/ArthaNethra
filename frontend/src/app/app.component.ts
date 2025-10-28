import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-gray-50">
      <!-- Header -->
      <header class="bg-white shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="h-10 w-10 bg-gradient-to-br from-primary-600 to-accent-600 rounded-lg flex items-center justify-center">
                <span class="text-white font-bold text-xl">AN</span>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-gray-900">ArthaNethra</h1>
                <p class="text-sm text-gray-500">AI Financial Risk Investigator</p>
              </div>
            </div>
            <nav class="flex space-x-4">
              <a routerLink="/" routerLinkActive="text-primary-600" [routerLinkActiveOptions]="{exact: true}" 
                 class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium">
                Dashboard
              </a>
              <a routerLink="/upload" routerLinkActive="text-primary-600"
                 class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium">
                Upload
              </a>
              <a routerLink="/graph" routerLinkActive="text-primary-600"
                 class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium">
                Graph
              </a>
              <a routerLink="/chat" routerLinkActive="text-primary-600"
                 class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium">
                Chat
              </a>
              <a routerLink="/risks" routerLinkActive="text-primary-600"
                 class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium">
                Risks
              </a>
            </nav>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <router-outlet></router-outlet>
      </main>

      <!-- Footer -->
      <footer class="bg-white border-t border-gray-200 mt-12">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p class="text-center text-sm text-gray-500">
            © 2025 ArthaNethra. Built for Financial AI Hackathon Championship 2025.
          </p>
        </div>
      </footer>
    </div>
  `,
  styles: []
})
export class AppComponent {
  title = 'ArthaNethra';
}

