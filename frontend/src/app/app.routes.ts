import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'chat',
    pathMatch: 'full'
  },
  {
    path: 'chat',
    loadComponent: () => import('./components/chat-unified/chat-unified.component').then(m => m.ChatUnifiedComponent)
  },
  {
    path: '**',
    redirectTo: 'chat'
  }
];

