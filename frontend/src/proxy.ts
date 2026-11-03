// Contains the middleware for a quick validation that a cookie exists.
// Redirect to sign-in if no cookie exists
import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

const PUBLIC_PATHS = ["/sign-in", "/sign-up"];

export function proxy(request: NextRequest) {
  if (!PUBLIC_PATHS.includes(request.nextUrl.pathname) && !getSessionCookie(request)) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Skip the auth API, Next.js assets and files in /public.
  matcher: ["/((?!api|_next/static|_next/image|.*\\..*).*)"],
};