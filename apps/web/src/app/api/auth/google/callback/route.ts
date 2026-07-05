import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  const error = req.nextUrl.searchParams.get("error");

  if (error) {
    return NextResponse.redirect(
      new URL(`/?auth_error=${encodeURIComponent(error)}`, req.url)
    );
  }

  if (!code) {
    return NextResponse.redirect(new URL("/?auth_error=missing_code", req.url));
  }

  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  
  // Normalize origin: Google OAuth rejects 0.0.0.0 or 127.0.0.1
  let origin = req.nextUrl.origin;
  if (origin.includes("0.0.0.0") || origin.includes("127.0.0.1")) {
    origin = origin.replace("0.0.0.0", "localhost").replace("127.0.0.1", "localhost");
  }
  const redirectUri = `${origin}/api/auth/google/callback`;

  if (!clientId || !clientSecret) {
    return NextResponse.redirect(
      new URL("/?auth_error=missing_google_credentials", origin)
    );
  }

  try {
    // Exchange the authorization code for tokens
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri,
        grant_type: "authorization_code",
      }).toString(),
    });

    if (!tokenRes.ok) {
      const errData = await tokenRes.json().catch(() => ({}));
      console.error("Token exchange failed:", errData);
      return NextResponse.redirect(
        new URL("/?auth_error=token_exchange_failed", origin)
      );
    }

    const tokens = await tokenRes.json();
    const accessToken: string = tokens.access_token;
    const idToken: string = tokens.id_token;

    // Decode the ID token (JWT, no signature verification needed for profile data here)
    let userName = "Founder";
    let userEmail = "";
    let userPicture = "";
    try {
      const payload = JSON.parse(
        Buffer.from(idToken.split(".")[1], "base64url").toString("utf-8")
      );
      userName = payload.name || payload.given_name || "Founder";
      userEmail = payload.email || "";
      userPicture = payload.picture || "";
    } catch (e) {
      console.warn("ID token decode failed:", e);
    }

    // Build redirect URL passing tokens and user info as query params (short-lived, picked up by client)
    const redirectUrl = new URL("/", origin);
    redirectUrl.searchParams.set("google_access_token", accessToken);
    redirectUrl.searchParams.set("google_token_saved_at", Date.now().toString());
    redirectUrl.searchParams.set("user_name", userName);
    redirectUrl.searchParams.set("user_email", userEmail);
    if (userPicture) redirectUrl.searchParams.set("user_picture", userPicture);

    return NextResponse.redirect(redirectUrl);
  } catch (err: any) {
    console.error("Google OAuth callback error:", err);
    return NextResponse.redirect(
      new URL(`/?auth_error=${encodeURIComponent(err.message || "Unknown error")}`, origin)
    );
  }
}
