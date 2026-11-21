import Link from "next/link";

export function SiteHeader({ signedIn = false }: { signedIn?: boolean }) {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-5">
      <Link href="/" className="text-sm font-semibold tracking-[0.22em] text-stone-900">
        MNEMO
      </Link>
      <nav className="flex items-center gap-3 text-sm">
        {signedIn ? (
          <Link href="/learn" className="rounded bg-stone-900 px-3 py-2 text-white">
            Teacher Mode
          </Link>
        ) : (
          <>
            <Link href="/signin" className="rounded px-3 py-2 text-stone-700 hover:text-stone-950">
              Sign in
            </Link>
            <Link href="/signup" className="rounded bg-stone-900 px-3 py-2 text-white">
              Create account
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
