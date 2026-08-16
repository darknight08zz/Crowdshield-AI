import { WS_BASE_URL, API_BASE_URL } from './constants';
import { api, RealtimeInferenceResultData } from './api';
import { globalTemporalHistoryStore } from './temporalHistoryStore';

export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'ERROR';

export interface SubscriptionKey {
  eventId: string;
  cameraId: string;
  zoneId: string;
}

export interface RealtimeInferenceState {
  connectionStatus: ConnectionStatus;
  data: RealtimeInferenceResultData | null;
  error: string | null;
  lastUpdatedTimestamp: string | null;
}

export type InferenceCallback = (state: RealtimeInferenceState) => void;

export class RealtimeInferenceClient {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private token: string | null = null;
  private currentSubscription: SubscriptionKey | null = null;
  private callbacks: Set<InferenceCallback> = new Set();
  private state: RealtimeInferenceState = {
    connectionStatus: 'DISCONNECTED',
    data: null,
    error: null,
    lastUpdatedTimestamp: null,
  };

  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;

  constructor(wsBaseUrl?: string) {
    this.wsUrl = wsBaseUrl || WS_BASE_URL;
  }

  public setToken(token: string | null) {
    this.token = token;
  }

  public getState(): RealtimeInferenceState {
    return { ...this.state };
  }

  public subscribeState(callback: InferenceCallback): () => void {
    this.callbacks.add(callback);
    callback(this.getState());
    return () => {
      this.callbacks.delete(callback);
    };
  }

  private updateState(partialState: Partial<RealtimeInferenceState>) {
    this.state = { ...this.state, ...partialState };
    this.callbacks.forEach((cb) => cb(this.getState()));
  }

  /**
   * Initial REST snapshot fetch before WebSocket stream updates.
   * Ensures UI immediately receives latest known state without waiting for next WS frame.
   */
  public async loadInitialSnapshot(cameraId: string, zoneId?: string): Promise<RealtimeInferenceResultData | null> {
    try {
      let snapshot: RealtimeInferenceResultData | null = null;
      if (zoneId) {
        snapshot = await api.fetchZoneInference(cameraId, zoneId, this.token || undefined);
      } else {
        snapshot = await api.fetchCameraInference(cameraId, this.token || undefined);
      }

      if (snapshot) {
        this.processIncomingPayload(snapshot, 'REST');
      }
      return snapshot;
    } catch (e: any) {
      console.warn(`[RealtimeInferenceClient] Snapshot fetch failed: ${e.message || e}`);
      // Do NOT inject fake mock data; set state cleanly
      if (!this.state.data) {
        this.updateState({
          error: `REST snapshot unavailable (${e.message || 'Network error'})`,
        });
      }
      return null;
    }
  }

  /**
   * Connects WebSocket stream and subscribes to (eventId, cameraId, zoneId).
   */
  public connect(subscription: SubscriptionKey, token?: string) {
    if (token !== undefined) {
      this.token = token;
    }

    const isSameSub =
      this.currentSubscription &&
      this.currentSubscription.eventId === subscription.eventId &&
      this.currentSubscription.cameraId === subscription.cameraId &&
      this.currentSubscription.zoneId === subscription.zoneId;

    if (this.ws && this.ws.readyState === WebSocket.OPEN && isSameSub) {
      return; // Already connected and subscribed to target stream
    }

    // Switch subscription if target camera/zone changed
    if (this.currentSubscription && !isSameSub) {
      this.clearPreviousStreamData();
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendUnsubscribe(this.currentSubscription);
      }
    }

    this.currentSubscription = subscription;
    this.isIntentionallyClosed = false;

    // Load initial REST snapshot in background
    this.loadInitialSnapshot(subscription.cameraId, subscription.zoneId);

    // Build WS connection URL with auth token
    let fullUrl = this.wsUrl;
    let effectiveToken = this.token;
    if (!effectiveToken && typeof window !== 'undefined') {
      effectiveToken = localStorage.getItem('token') || sessionStorage.getItem('token') || null;
    }
    if (effectiveToken) {
      const sep = fullUrl.includes('?') ? '&' : '?';
      fullUrl = `${fullUrl}${sep}token=${encodeURIComponent(effectiveToken)}`;
    }

    this.closeWebSocketOnly();
    this.updateState({ connectionStatus: this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING', error: null });

    try {
      this.ws = new WebSocket(fullUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateState({ connectionStatus: 'CONNECTED', error: null });
        this.sendSubscribe(subscription);
        this.startPingLoop();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.ws.onerror = (event) => {
        console.error('[RealtimeInferenceClient] WebSocket error:', event);
        this.updateState({ error: 'WebSocket connection error' });
      };

      this.ws.onclose = (event) => {
        this.stopPingLoop();
        if (!this.isIntentionallyClosed) {
          this.updateState({ connectionStatus: 'DISCONNECTED' });
          this.scheduleReconnect();
        } else {
          this.updateState({ connectionStatus: 'DISCONNECTED' });
        }
      };
    } catch (e: any) {
      console.error('[RealtimeInferenceClient] Failed to initialize WebSocket:', e);
      this.updateState({ connectionStatus: 'ERROR', error: e.message || 'Connection failed' });
      this.scheduleReconnect();
    }
  }

  private sendSubscribe(sub: SubscriptionKey) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'subscribe',
          event_id: sub.eventId,
          camera_id: sub.cameraId,
          zone_id: sub.zoneId,
        })
      );
    }
  }

  private sendUnsubscribe(sub: SubscriptionKey) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'unsubscribe',
          event_id: sub.eventId,
          camera_id: sub.cameraId,
          zone_id: sub.zoneId,
        })
      );
    }
  }

  private startPingLoop() {
    this.stopPingLoop();
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000);
  }

  private stopPingLoop() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private handleMessage(rawMessage: string) {
    try {
      const payload = JSON.parse(rawMessage);
      if (payload.type === 'INFERENCE_UPDATE' && payload.data) {
        // Validate subscription key match to prevent cross-stream pollution
        const camId = payload.camera_id || payload.data.camera_id;
        const zId = payload.zone_id || payload.data.zone_id;
        if (
          this.currentSubscription &&
          (camId === this.currentSubscription.cameraId || !camId) &&
          (zId === this.currentSubscription.zoneId || !zId)
        ) {
          this.processIncomingPayload(payload.data, 'WEBSOCKET');
        }
      } else if (payload.type === 'subscription_confirmed' || payload.type === 'SUBSCRIPTION_CONFIRMED') {
        // Confirmed subscription
      } else if (payload.type === 'pong' || payload.type === 'PONG') {
        // Heartbeat response
      }
    } catch (e) {
      console.error('[RealtimeInferenceClient] Failed to parse WebSocket message:', e);
    }
  }

  /**
   * Prevents race conditions by rejecting out-of-order older payloads.
   */
  private processIncomingPayload(payload: RealtimeInferenceResultData, source: 'REST' | 'WEBSOCKET') {
    // Normalize physics risk score alias
    if (payload && payload.current_physics_risk !== undefined && payload.current_risk_score === undefined) {
      payload.current_risk_score = payload.current_physics_risk;
    } else if (payload && payload.current_risk_score !== undefined && payload.current_physics_risk === undefined) {
      payload.current_physics_risk = payload.current_risk_score;
    }

    // Basic validation
    if (!payload || (typeof payload.current_risk_score !== 'number' && typeof payload.current_physics_risk !== 'number')) {
      console.warn('[RealtimeInferenceClient] Invalid inference payload rejected');
      return;
    }

    const newTsString = payload.telemetry_timestamp || payload.prediction_timestamp || new Date().toISOString();
    const newTime = new Date(newTsString).getTime();

    if (this.state.lastUpdatedTimestamp) {
      const currentTime = new Date(this.state.lastUpdatedTimestamp).getTime();
      if (newTime < currentTime) {
        // Stale out-of-order update, ignore
        return;
      }
    }

    // Automatically record sample into isolated stream history store
    globalTemporalHistoryStore.addSample(payload);

    this.updateState({
      data: payload,
      lastUpdatedTimestamp: newTsString,
      error: null,
    });
  }

  private scheduleReconnect() {
    if (this.isIntentionallyClosed || this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.updateState({ connectionStatus: 'ERROR', error: 'Max reconnection attempts reached' });
      }
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000);
    this.updateState({ connectionStatus: 'RECONNECTING' });

    this.clearReconnectTimer();
    this.reconnectTimer = setTimeout(() => {
      if (this.currentSubscription && !this.isIntentionallyClosed) {
        this.connect(this.currentSubscription);
      }
    }, delay);
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearPreviousStreamData() {
    this.updateState({
      data: null,
      lastUpdatedTimestamp: null,
    });
  }

  private closeWebSocketOnly() {
    this.stopPingLoop();
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
  }

  public disconnect() {
    this.isIntentionallyClosed = true;
    this.clearReconnectTimer();
    this.closeWebSocketOnly();
    this.currentSubscription = null;
    this.updateState({
      connectionStatus: 'DISCONNECTED',
      data: null,
      error: null,
      lastUpdatedTimestamp: null,
    });
  }
}

// Global client singleton instance for shared connection management
export const globalRealtimeClient = new RealtimeInferenceClient();
