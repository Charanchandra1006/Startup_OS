import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 relative overflow-hidden w-full font-sans">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-100/50 blur-[120px] mix-blend-multiply" />
        <div className="absolute top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full bg-indigo-100/40 blur-[120px] mix-blend-multiply" />
        <div className="absolute -bottom-[20%] left-[20%] w-[50%] h-[50%] rounded-full bg-purple-100/40 blur-[120px] mix-blend-multiply" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6 py-12 flex flex-col items-center">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-black text-white font-bold text-xl mb-4 shadow-xl">
            C
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">Chief AI</h1>
          <p className="text-gray-500 mt-2 font-medium">Your Startup's Operating System</p>
        </div>

        <SignUp />
      </div>
    </div>
  );
}
