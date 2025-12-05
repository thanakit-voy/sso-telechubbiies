import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Paths that don't require authentication
const publicPaths = ["/", "/invite/accept", "/oauth/authorize", "/oauth/callback"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if this is a public path
  const isPublicPath = publicPaths.some(
    (path) => pathname === path || pathname.startsWith(path)
  );

  if (isPublicPath) {
    return NextResponse.next();
  }

  // Check for refresh_token cookie (indicates user might be logged in)
  const refreshToken = request.cookies.get("refresh_token");

  if (!refreshToken && pathname.startsWith("/dashboard")) {
    // Redirect to login
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
