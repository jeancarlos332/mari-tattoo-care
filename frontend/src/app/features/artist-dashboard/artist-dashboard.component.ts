
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import QRCode from 'qrcode';

import {
  TattooSession,
  TattooSessionCreated,
  TattooSessionService,
} from '../../core/services/tattoo-session.service';

@Component({
  selector: 'app-artist-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './artist-dashboard.component.html',
  styleUrl: './artist-dashboard.component.css',
})
export class ArtistDashboardComponent implements OnInit {
  private readonly tattooSessionService = inject(TattooSessionService);
  private readonly cdr = inject(ChangeDetectorRef);

  selectedSessionForDeletion: TattooSession | null = null;
  deletingSessionId: string | null = null;
  deleteErrorMessage = '';

  selectedSessionForQr: TattooSession | null = null;
  accessActionSessionId: string | null = null;

  readonly artistId = 'aacd1cd1-150e-4b22-a146-129e756c98e2';

  sessions: TattooSession[] = [];

  loading = true;
  saving = false;
  showCreateModal = false;
  showQrModal = false;
  generatingQr = false;

  errorMessage = '';
  saveErrorMessage = '';
  successMessage = '';
  qrErrorMessage = '';
  copyMessage = '';

  createdClientName = '';
  createdAccessUrl = '';
  createdQrCode = '';
  createdAccessExpiresAt = '';

  clientName = '';
  clientPhone = '';
  tattooDescription = '';
  tattooedAt = this.getTodayLocalDate();

  ngOnInit(): void {
    this.loadSessions();
  }

  private getTodayLocalDate(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  openCreateModal(): void {
    this.resetForm();
    this.showCreateModal = true;
    this.cdr.detectChanges();
  }

  closeCreateModal(): void {
    if (this.saving) {
      return;
    }

    this.showCreateModal = false;
    this.saveErrorMessage = '';
    this.cdr.detectChanges();
  }

  closeQrModal(): void {
    this.showQrModal = false;
    this.copyMessage = '';
    this.cdr.detectChanges();
  }

  private resetForm(): void {
    this.clientName = '';
    this.clientPhone = '';
    this.tattooDescription = '';
    this.tattooedAt = this.getTodayLocalDate();
    this.saveErrorMessage = '';
  }

  loadSessions(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.tattooSessionService.getSessions(this.artistId).subscribe({
      next: (sessions) => {
        this.sessions = sessions;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error al consultar los seguimientos:', error);

        this.errorMessage =
          'No fue posible cargar los seguimientos. Verifica el backend e inténtalo nuevamente.';

        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  createSession(): void {
    const name = this.clientName.trim();

    if (name.length < 2 || !this.tattooedAt || this.saving) {
      return;
    }

    this.saving = true;
    this.saveErrorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    const payload = {
      artist_id: this.artistId,
      client_name: name,
      client_phone: this.clientPhone.trim() || null,
      tattoo_description: this.tattooDescription.trim() || null,
      tattooed_at: new Date(`${this.tattooedAt}T12:00:00`).toISOString(),
      follow_up_days: 30,
    };

    this.tattooSessionService.createSession(payload).subscribe({
      next: (createdSession: TattooSessionCreated) => {
        this.showCreateModal = false;
        this.saving = false;
        this.successMessage = 'Tatuaje registrado correctamente.';

        this.selectedSessionForQr = null;
        this.createdClientName = createdSession.client_name;
        this.createdAccessUrl = createdSession.access_url;
        this.createdAccessExpiresAt = createdSession.access_expires_at;
        this.createdQrCode = '';
        this.qrErrorMessage = '';
        this.copyMessage = '';
        this.showQrModal = true;

        this.resetForm();
        this.generateQrCode(createdSession.access_url);

        this.loadSessions();
      },
      error: (error) => {
        console.error('Error al registrar el tatuaje:', error);

        this.saveErrorMessage =
          error.status === 404
            ? 'No se encontró el tatuador configurado.'
            : 'No fue posible guardar el tatuaje. Revisa la conexión e inténtalo nuevamente.';

        this.saving = false;
        this.cdr.detectChanges();
      },
    });
  }


  openSessionQr(session: TattooSession): void {
    if (this.accessActionSessionId) {
      return;
    }

    this.accessActionSessionId = session.session_id;
    this.qrErrorMessage = '';
    this.copyMessage = '';
    this.cdr.detectChanges();

    this.tattooSessionService
      .getSessionAccessLink(session.session_id, this.artistId)
      .subscribe({
        next: (access) => {
          this.selectedSessionForQr = session;
          this.createdClientName = session.client_name;
          this.createdAccessUrl = access.access_url;
          this.createdAccessExpiresAt = access.access_expires_at;
          this.createdQrCode = '';
          this.showQrModal = true;
          this.accessActionSessionId = null;

          this.generateQrCode(access.access_url);
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error al recuperar el enlace:', error);

          this.qrErrorMessage =
            error.status === 404 || error.status === 409
              ? 'Este enlace no se puede recuperar. Regenera el acceso para generar un QR nuevo.'
              : 'No fue posible recuperar el enlace. Verifica la conexión e inténtalo nuevamente.';

          this.accessActionSessionId = null;
          this.cdr.detectChanges();
        },
      });
  }

  regenerateSessionAccess(session: TattooSession): void {
    if (this.accessActionSessionId) {
      return;
    }

    const confirmed = window.confirm(
      `¿Regenerar el acceso de ${session.client_name}? El enlace anterior dejará de funcionar.`,
    );

    if (!confirmed) {
      return;
    }

    this.accessActionSessionId = session.session_id;
    this.qrErrorMessage = '';
    this.copyMessage = '';
    this.cdr.detectChanges();

    this.tattooSessionService
      .regenerateSessionAccessLink(session.session_id, this.artistId)
      .subscribe({
        next: (access) => {
          this.selectedSessionForQr = session;
          this.createdClientName = session.client_name;
          this.createdAccessUrl = access.access_url;
          this.createdAccessExpiresAt = access.access_expires_at;
          this.createdQrCode = '';
          this.showQrModal = true;
          this.accessActionSessionId = null;

          this.generateQrCode(access.access_url);
          this.successMessage = 'Acceso regenerado correctamente.';
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error al regenerar el acceso:', error);

          this.qrErrorMessage =
            error.status === 404
              ? 'No se encontró una sesión activa para regenerar el acceso.'
              : 'No fue posible regenerar el acceso. Inténtalo nuevamente.';

          this.accessActionSessionId = null;
          this.cdr.detectChanges();
        },
      });
  }


  copySessionAccessLink(session: TattooSession): void {
    if (this.accessActionSessionId) {
      return;
    }

    this.accessActionSessionId = session.session_id;
    this.copyMessage = '';
    this.qrErrorMessage = '';
    this.cdr.detectChanges();

    this.tattooSessionService
      .getSessionAccessLink(session.session_id, this.artistId)
      .subscribe({
        next: async (access) => {
          this.createdClientName = session.client_name;
          this.createdAccessUrl = access.access_url;
          this.createdAccessExpiresAt = access.access_expires_at;
          this.selectedSessionForQr = session;
          
          try {
            await navigator.clipboard.writeText(access.access_url);
            this.copyMessage = 'Enlace copiado correctamente.';
          } catch {
            this.copyMessage =
              'No se pudo copiar automáticamente. Abre el QR para copiar el enlace manualmente.';
          }

          this.accessActionSessionId = null;
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error al consultar el enlace para copiar:', error);

          this.qrErrorMessage =
            error.status === 404 || error.status === 409
              ? 'No hay un enlace vigente recuperable. Regenera el acceso primero.'
              : 'No fue posible obtener el enlace. Inténtalo nuevamente.';

          this.accessActionSessionId = null;
          this.cdr.detectChanges();
        },
      });
  }

  private generateQrCode(accessUrl: string): void {
    this.generatingQr = true;
    this.createdQrCode = '';
    this.cdr.detectChanges();

    QRCode.toDataURL(accessUrl, {
      width: 300,
      margin: 2,
      errorCorrectionLevel: 'M',
    })
      .then((dataUrl: string) => {
        this.createdQrCode = dataUrl;
        this.generatingQr = false;
        this.cdr.detectChanges();
      })
      .catch((error: unknown) => {
        console.error('Error al generar el QR:', error);

        this.qrErrorMessage =
          'No fue posible generar el código QR. Puedes copiar el enlace privado.';
        this.generatingQr = false;
        this.cdr.detectChanges();
      });
  }

  async copyAccessLink(): Promise<void> {
    if (!this.createdAccessUrl) {
      return;
    }

    try {
      await navigator.clipboard.writeText(this.createdAccessUrl);
      this.copyMessage = 'Enlace copiado correctamente.';
    } catch {
      this.copyMessage =
        'No se pudo copiar automáticamente. Selecciona y copia el enlace manualmente.';
    }

    this.cdr.detectChanges();
  }

  get activeSessions(): number {
    return this.sessions.filter((session) => session.active).length;
  }

  formatDate(date: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      dateStyle: 'medium',
      timeZone: 'America/Bogota',
    }).format(new Date(date));
  }

  requestDeleteSession(session: TattooSession): void {
    this.selectedSessionForDeletion = session;
    this.deleteErrorMessage = '';
    this.cdr.detectChanges();
  }

  cancelDeleteSession(): void {
    if (this.deletingSessionId) {
      return;
    }

    this.selectedSessionForDeletion = null;
    this.deleteErrorMessage = '';
    this.cdr.detectChanges();
  }

  confirmDeleteSession(): void {
    const session = this.selectedSessionForDeletion;

    if (!session || this.deletingSessionId) {
      return;
    }

    this.deletingSessionId = session.session_id;
    this.deleteErrorMessage = '';
    this.cdr.detectChanges();

    this.tattooSessionService
      .deleteSession(session.session_id, this.artistId)
      .subscribe({
        next: () => {
          this.sessions = this.sessions.filter(
            (item) => item.session_id !== session.session_id,
          );

          this.selectedSessionForDeletion = null;
          this.deletingSessionId = null;
          this.successMessage = 'Seguimiento eliminado correctamente.';
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error al eliminar el seguimiento:', error);

          this.deleteErrorMessage =
            error.status === 404
              ? 'Este seguimiento ya no existe o no está disponible.'
              : 'No fue posible eliminar el seguimiento. Inténtalo nuevamente.';

          this.deletingSessionId = null;
          this.cdr.detectChanges();
        },
      });
  }
}
