"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main role="alert" className="mx-auto max-w-lg px-4 py-16">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="mt-2 text-stone-700">The page could not be displayed. Try again.</p>
      {reset ? (
        <button type="button" onClick={reset} className="mt-4 rounded bg-stone-900 px-3 py-2 text-sm text-white">
          Try again
        </button>
      ) : null}
    </main>
  );
}
