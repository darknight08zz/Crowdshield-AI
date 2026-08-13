import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET() {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get('user_session')?.value;
  const accessToken = cookieStore.get('access_token')?.value;

  if (!sessionCookie || !accessToken) {
    return NextResponse.json({ authenticated: false, user: null }, { status: 200 });
  }

  try {
    const user = JSON.parse(sessionCookie);
    return NextResponse.json({ authenticated: true, user });
  } catch {
    return NextResponse.json({ authenticated: false, user: null }, { status: 200 });
  }
}

