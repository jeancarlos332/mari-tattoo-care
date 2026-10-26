
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/home/home.component').then(
        (module) => module.HomeComponent,
      ),
  },
  {
    path: 'seguimiento',
    loadComponent: () =>
      import('./features/client-follow-up/client-follow-up.component').then(
        (module) => module.ClientFollowUpComponent,
      ),
  },
  {
    path: 'mari',
    loadComponent: () =>
      import('./features/artist-dashboard/artist-dashboard.component').then(
        (module) => module.ArtistDashboardComponent,
      ),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
