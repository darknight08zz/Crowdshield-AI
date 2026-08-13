import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Define public paths that bypass auth checks
  const isPublicPath =
    pathname.startsWith('/auth') ||
    pathname.startsWith('/api/auth') ||
    pathname === '/unauthorized' ||
    pathname.startsWith('/_next') ||
    pathname === '/favicon.ico';

  if (isPublicPath) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get('access_token')?.value;
  const userSessionCookie = request.cookies.get('user_session')?.value;

  // If no auth token or session present, redirect to login
  if (!accessToken || !userSessionCookie) {
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  let userRole = '';
  try {
    const userSession = JSON.parse(userSessionCookie);
    userRole = userSession.role || '';
  } catch (e) {
    const loginUrl = new URL('/auth/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // System Admin route protection
  if (pathname.startsWith('/admin/system')) {
    if (userRole !== 'system_admin') {
      const unauthUrl = new URL('/unauthorized', request.url);
      unauthUrl.searchParams.set('required', 'System Administrator');
      unauthUrl.searchParams.set('current', userRole);
      return NextResponse.redirect(unauthUrl);
    }
  }

  // Event Admin route protection
  if (pathname.startsWith('/admin/event')) {
    if (userRole !== 'event_admin' && userRole !== 'system_admin') {
      const unauthUrl = new URL('/unauthorized', request.url);
      unauthUrl.searchParams.set('required', 'Event Administrator');
      unauthUrl.searchParams.set('current', userRole);
      return NextResponse.redirect(unauthUrl);
    }
  }

  // Command Room & Staff routes protection
  if (
    pathname.startsWith('/overview') ||
    pathname.startsWith('/incidents') ||
    pathname.startsWith('/zones') ||
    pathname.startsWith('/officers')
  ) {
    const allowedStaffRoles = ['operator', 'field_officer', 'event_admin', 'system_admin'];
    if (!allowedStaffRoles.includes(userRole)) {
      const unauthUrl = new URL('/unauthorized', request.url);
      unauthUrl.searchParams.set('required', 'Command Room Staff');
      unauthUrl.searchParams.set('current', userRole);
      return NextResponse.redirect(unauthUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
