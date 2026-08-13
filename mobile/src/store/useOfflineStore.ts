import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

export interface QueuedIncident {
  id: string;
  type: string;
  description: string;
  lat: number;
  lng: number;
  image_uri?: string;
  created_at: string;
}

interface OfflineState {
  queuedIncidents: QueuedIncident[];
  isOnline: boolean;
  setIsOnline: (online: boolean) => void;
  enqueueIncident: (incident: Omit<QueuedIncident, 'id' | 'created_at'>) => Promise<void>;
  removeQueuedIncident: (id: string) => Promise<void>;
  loadQueue: () => Promise<void>;
}

const STORAGE_KEY = 'CROWDSHIELD_OFFLINE_QUEUE_V1';

export const useOfflineStore = create<OfflineState>((set, get) => ({
  queuedIncidents: [],
  isOnline: true,
  setIsOnline: (online) => set({ isOnline: online }),

  loadQueue: async () => {
    try {
      const raw = await SecureStore.getItemAsync(STORAGE_KEY);
      if (raw) {
        set({ queuedIncidents: JSON.parse(raw) });
      }
    } catch (e) {
      console.warn('Failed to load offline queue:', e);
    }
  },

  enqueueIncident: async (incidentData) => {
    const item: QueuedIncident = {
      ...incidentData,
      id: `offline-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      created_at: new Date().toISOString(),
    };
    const updated = [...get().queuedIncidents, item];
    set({ queuedIncidents: updated });
    await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(updated));
  },

  removeQueuedIncident: async (id) => {
    const updated = get().queuedIncidents.filter((item) => item.id !== id);
    set({ queuedIncidents: updated });
    await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(updated));
  },
}));
