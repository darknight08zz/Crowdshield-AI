import { useEffect, useState, useCallback, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  globalRealtimeClient,
  RealtimeInferenceState,
  SubscriptionKey,
} from './realtimeInferenceClient';
import {
  globalTemporalHistoryStore,
  TemporalSample,
  AlertStateTransition,
} from './temporalHistoryStore';

export type PresentationalTrendLabel = 'ESCALATING' | 'RECOVERING' | 'STABLE' | 'INSUFFICIENT_DATA';

export function computePresentationalTrend(samples: TemporalSample[], metric: 'density' | 'current_physics_risk' | 'ai_probability'): PresentationalTrendLabel {
  if (!samples || samples.length < 3) {
    return 'INSUFFICIENT_DATA';
  }

  const recentWindow = samples.slice(-5);
  const firstVal = recentWindow[0][metric];
  const lastVal = recentWindow[recentWindow.length - 1][metric];

  if (firstVal === null || lastVal === null) {
    return 'INSUFFICIENT_DATA';
  }

  const diff = lastVal - firstVal;
  const threshold = metric === 'density' ? 0.2 : 3.0; // 0.2 p/m2 or 3 risk points

  if (diff > threshold) return 'ESCALATING';
  if (diff < -threshold) return 'RECOVERING';
  return 'STABLE';
}

export function useRealtimeInference(subscription: SubscriptionKey | null = null) {
  const [state, setState] = useState<RealtimeInferenceState>(() => globalRealtimeClient.getState());
  const [history, setHistory] = useState<TemporalSample[]>([]);
  const [transitions, setTransitions] = useState<AlertStateTransition[]>([]);
  const [globalTransitions, setGlobalTransitions] = useState<AlertStateTransition[]>([]);

  useEffect(() => {
    let isMounted = true;
    const supabase = createClient();

    async function initStream() {
      if (!subscription || !subscription.cameraId) return;

      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token || null;

      if (!isMounted) return;
      globalRealtimeClient.connect(subscription, token || undefined);
    }

    const unsubscribeClientState = globalRealtimeClient.subscribeState((newState) => {
      if (isMounted) {
        setState(newState);
      }
    });

    const unsubscribeHistoryStore = globalTemporalHistoryStore.subscribe(() => {
      if (isMounted && subscription) {
        const currentHistory = globalTemporalHistoryStore.getHistory(
          subscription.eventId,
          subscription.cameraId,
          subscription.zoneId
        );
        const currentTransitions = globalTemporalHistoryStore.getTransitions(
          subscription.eventId,
          subscription.cameraId,
          subscription.zoneId
        );
        setHistory(currentHistory);
        setTransitions(currentTransitions);
        setGlobalTransitions(globalTemporalHistoryStore.getGlobalTransitions());
      }
    });

    initStream();

    return () => {
      isMounted = false;
      unsubscribeClientState();
      unsubscribeHistoryStore();
      globalRealtimeClient.disconnect();
    };
  }, [subscription?.eventId, subscription?.cameraId, subscription?.zoneId]);

  const reloadSnapshot = useCallback(async () => {
    if (subscription?.cameraId) {
      return await globalRealtimeClient.loadInitialSnapshot(subscription.cameraId, subscription.zoneId);
    }
    return null;
  }, [subscription?.cameraId, subscription?.zoneId]);

  const densityTrend = useMemo(() => computePresentationalTrend(history, 'density'), [history]);
  const physicsRiskTrend = useMemo(() => computePresentationalTrend(history, 'current_physics_risk'), [history]);
  const aiProbabilityTrend = useMemo(() => computePresentationalTrend(history, 'ai_probability'), [history]);

  return {
    ...state,
    history,
    transitions,
    globalTransitions,
    densityTrend,
    physicsRiskTrend,
    aiProbabilityTrend,
    reloadSnapshot,
  };
}
