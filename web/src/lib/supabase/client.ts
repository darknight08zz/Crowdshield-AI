import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  );
}

export function setRealtimeAuth(client: any, accessToken: string) {
  if (client && accessToken && client.realtime) {
    client.realtime.setAuth(accessToken);
  }
}
