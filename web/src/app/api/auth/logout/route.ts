import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { API_BASE_URL } from '@/lib/constants';

export async function POST() {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (accessToken) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }).catch(() => {});
    }

    cookieStore.delete('access_token');
    cookieStore.delete('refresh_token');
    cookieStore.delete('user_session');

    return NextResponse.json({ success: true, message: 'Logged out successfully' });
  } catch (error: any) {
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}
