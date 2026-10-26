
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import {
  TattooFollowUpAccess,
  TattooSessionService,
} from '../../core/services/tattoo-session.service';

@Component({
  selector: 'app-client-follow-up',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './client-follow-up.component.html',
  styleUrl: './client-follow-up.component.css',
})
export class ClientFollowUpComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly tattooSessionService = inject(TattooSessionService);
  private readonly cdr = inject(ChangeDetectorRef);

  access: TattooFollowUpAccess | null = null;
  loading = true;
  accessError = '';

  selectedPhoto: string | null = null;
  selectedFileName = '';
  photoError = '';
  observation = '';
  photoConfirmed = false;

  private objectUrl: string | null = null;

  readonly today = new Date();

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.loading = false;
      this.accessError =
        'Este enlace no contiene un código de acceso. Escanea el QR que te entregó Mari.';
      return;
    }

    this.tattooSessionService.getClientFollowUp(token).subscribe({
      next: (access) => {
        this.access = access;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('No fue posible validar el seguimiento:', error);

        this.accessError =
          error.status === 404
            ? 'Este enlace venció o ya no está disponible. Contacta a Mari para recibir uno nuevo.'
            : 'No pudimos cargar tu seguimiento. Comprueba tu conexión e inténtalo de nuevo.';

        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    this.photoError = '';
    this.photoConfirmed = false;

    if (!file) {
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.photoError = 'Selecciona un archivo de imagen válido.';
      input.value = '';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.photoError = 'La imagen debe pesar menos de 10 MB.';
      input.value = '';
      return;
    }

    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }

    this.objectUrl = URL.createObjectURL(file);
    this.selectedPhoto = this.objectUrl;
    this.selectedFileName = file.name;
  }

  confirmPhotoPreview(): void {
    if (!this.selectedPhoto) {
      this.photoError = 'Primero selecciona una fotografía.';
      return;
    }

    this.photoConfirmed = true;
    this.photoError = '';
  }

  formatDate(date: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      dateStyle: 'medium',
      timeZone: 'America/Bogota',
    }).format(new Date(date));
  }

  ngOnDestroy(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }
  }
}
