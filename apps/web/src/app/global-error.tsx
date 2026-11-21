"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body>
        <main role="alert" style={{ fontFamily: "Segoe UI, sans-serif", padding: "2rem" }}>
          <h1>Something went wrong</h1>
          <p>The application hit an unexpected error.</p>
          <button type="button" onClick={reset}>
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
