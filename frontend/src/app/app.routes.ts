import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'upload',
    loadComponent: () => import('./components/upload/upload.component').then(m => m.UploadComponent)
  },
  {
    path: 'documents',
    loadComponent: () => import('./components/documents/documents.component').then(m => m.DocumentsComponent)
  },
  {
    path: 'jobs',
    loadComponent: () => import('./components/jobs/jobs.component').then(m => m.JobsComponent)
  },
  {
    path: 'graph',
    loadComponent: () => import('./components/graph/graph.component').then(m => m.GraphComponent)
  },
  {
    path: 'chat',
    loadComponent: () => import('./components/chat/chat.component').then(m => m.ChatComponent)
  },
  {
    path: 'risks',
    loadComponent: () => import('./components/risks/risks.component').then(m => m.RisksComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];

