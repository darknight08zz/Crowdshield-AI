import { useOfflineStore } from '../store/useOfflineStore';
import { api } from './api';

export async function flushOfflineQueue() {
  const store = useOfflineStore.getState();
  const queue = store.queuedIncidents;

  if (queue.length === 0) return;

  console.log(`[Offline Queue Sync] Flushing ${queue.length} pending offline report(s)...`);

  for (const item of queue) {
    try {
      await api.submitIncident({
        type: item.type,
        description: `[OFFLINE SYNCED] ${item.description}`,
        lat: item.lat,
        lng: item.lng,
        image_uri: item.image_uri,
      });
      await store.removeQueuedIncident(item.id);
      console.log(`[Offline Queue Sync] Successfully synced incident ${item.id}`);
    } catch (err) {
      console.warn(`[Offline Queue Sync] Failed to sync ${item.id}, will retry on next connection:`, err);
      break; // Stop loop if network is still down
    }
  }
}
