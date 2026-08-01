"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    const error = searchParams.get("error");

    if (error) {
      router.replace(`/?auth_error=${encodeURIComponent(error)}`);
      return;
    }

    if (token) {
      // Decode JWT to get user info if possible, or just store it
      localStorage.setItem("chief_token", token);
      
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.email) {
          localStorage.setItem("chief_user_email", payload.email);
        }
      } catch (e) {
        console.warn("Could not decode JWT payload");
      }

      router.replace("/");
    } else {
      router.replace("/");
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-6 font-sans">
      <Loader2 className="h-8 w-8 text-black animate-spin mb-4" />
      <h2 className="text-sm font-bold text-black tracking-tight">Authenticating with Google...</h2>
      <p className="text-xs text-neutral-500 mt-2">Securely validating workspace permissions.</p>
    </div>
  );
}
