"use client";

import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // We already have Clerk for auth, but the python backend might pass back
    // a legacy token here. We can just ignore it or store it just in case,
    // and then redirect the user back to the dashboard.
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("chief_token", token);
    }
    
    // Redirect back to the main dashboard
    router.push("/");
  }, [router, searchParams]);

  return (
    <div className="flex items-center justify-center h-screen w-full bg-white text-black">
      <div className="flex flex-col items-center gap-4">
        <div className="h-6 w-6 border-2 border-neutral-300 border-t-black rounded-full animate-spin" />
        <p className="text-sm font-mono text-neutral-500">Completing authentication...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen w-full bg-white text-black">
        <div className="h-6 w-6 border-2 border-neutral-300 border-t-black rounded-full animate-spin" />
      </div>
    }>
      <CallbackHandler />
    </Suspense>
  );
}
