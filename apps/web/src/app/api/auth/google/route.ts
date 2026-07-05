import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const clientId = process.env.GOOGLE_CLIENT_ID;

  if (!clientId) {
    return NextResponse.json(
      { error: "GOOGLE_CLIENT_ID is not set in environment variables." },
      { status: 500 }
    );
  }

  // Normalize origin: Google OAuth rejects 0.0.0.0 or 127.0.0.1
  let origin = req.nextUrl.origin;
  if (origin.includes("0.0.0.0") || origin.includes("127.0.0.1")) {
    origin = origin.replace("0.0.0.0", "localhost").replace("127.0.0.1", "localhost");
  }
  const redirectUri = `${origin}/api/auth/google/callback`;

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    // Request Gmail + Calendar + profile scopes all at once
    scope: [
      "openid",
      "email",
      "profile",
      "https://www.googleapis.com/auth/gmail.readonly",
      "https://www.googleapis.com/auth/calendar.readonly",
    ].join(" "),
    access_type: "offline",   // get refresh_token too
    prompt: "consent",        // always show consent to ensure fresh token
  });

  const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

  return NextResponse.redirect(googleAuthUrl);
}
