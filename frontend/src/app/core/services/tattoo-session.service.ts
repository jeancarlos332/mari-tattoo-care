
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TattooSession {
  session_id: string;
  client_id: string;
  client_name: string;
  client_phone: string | null;
  artist_id: string;
  artist_name: string;
  tattoo_description: string | null;
  tattooed_at: string;
  follow_up_days: number;
  active: boolean;
  created_at: string;
}

export interface TattooSessionCreate {
  artist_id: string;
  client_name: string;
  client_phone: string | null;
  tattoo_description: string | null;
  tattooed_at: string;
  follow_up_days: number;
}

export interface TattooSessionCreated {
  session_id: string;
  client_id: string;
  artist_id: string;
  client_name: string;
  tattooed_at: string;
  follow_up_days: number;
  access_url: string;
  access_expires_at: string;
  status: string;
}

export interface SessionAccessLink {
  session_id: string;
  access_url: string;
  access_expires_at: string;
}

export interface TattooFollowUpAccess {
  session_id: string;
  client_name: string;
  artist_name: string;
  tattoo_description: string | null;
  tattooed_at: string;
  follow_up_days: number;
  access_expires_at: string;
}

@Injectable({
  providedIn: 'root',
})
export class TattooSessionService {
  private readonly http = inject(HttpClient);

  private readonly apiUrl = 'http://127.0.0.1:8000/api/tattoo-sessions';

  getSessions(
    artistId: string,
    limit = 50,
    offset = 0,
  ): Observable<TattooSession[]> {
    const params = new HttpParams()
      .set('artist_id', artistId)
      .set('limit', limit)
      .set('offset', offset);

    return this.http.get<TattooSession[]>(this.apiUrl, { params });
  }

  createSession(
    payload: TattooSessionCreate,
  ): Observable<TattooSessionCreated> {
    return this.http.post<TattooSessionCreated>(this.apiUrl, payload);
  }

  getSessionAccessLink(
    sessionId: string,
    artistId: string,
  ): Observable<SessionAccessLink> {
    const params = new HttpParams().set('artist_id', artistId);

    return this.http.get<SessionAccessLink>(
      `${this.apiUrl}/${sessionId}/access-link`,
      { params },
    );
  }

  regenerateSessionAccessLink(
    sessionId: string,
    artistId: string,
  ): Observable<SessionAccessLink> {
    const params = new HttpParams().set('artist_id', artistId);

    return this.http.post<SessionAccessLink>(
      `${this.apiUrl}/${sessionId}/access-link/regenerate`,
      null,
      { params },
    );
  }

  getClientFollowUp(
    token: string,
  ): Observable<TattooFollowUpAccess> {
    return this.http.get<TattooFollowUpAccess>(
      `${this.apiUrl}/access/${encodeURIComponent(token)}`,
    );
  }

  deleteSession(
    sessionId: string,
    artistId: string,
  ): Observable<void> {
    const params = new HttpParams().set('artist_id', artistId);

    return this.http.delete<void>(
      `${this.apiUrl}/${sessionId}`,
      { params },
    );
  }
}
