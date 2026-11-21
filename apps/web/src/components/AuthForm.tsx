"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { currentAccount, signinAccount, signupAccount, toUiError, UiError } from "@/lib/api";

type Mode = "signin" | "signup";

export function AuthForm({ mode }: { mode: Mode }) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);
  const signup = mode === "signup";

  useEffect(() => {
    let active = true;
    currentAccount()
      .then(() => {
        if (active) {
          window.location.assign("/learn");
        }
      })
      .catch(() => {
        // A missing session stays on this form.
      });
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const nextEmail = email.trim();
    const nextName = displayName.trim();
    if (signup && !nextName) {
      setError({ code: "validation_error", message: "Display name is required.", requestId: null });
      return;
    }
    if (!nextEmail || !password || (signup && password.length < 8)) {
      setError({
        code: "validation_error",
        message: signup
          ? "Use an email and a password of at least 8 characters."
          : "Enter the email and password for your account.",
        requestId: null,
      });
      return;
    }
    setPending(true);
    try {
      if (signup) {
        await signupAccount(nextName, nextEmail, password);
      } else {
        await signinAccount(nextEmail, password);
      }
      window.location.assign("/learn");
    } catch (caught) {
      setError(toUiError(caught));
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-12">
      <Link href="/" className="text-sm font-semibold tracking-[0.22em] text-stone-900">
        MNEMO
      </Link>
      <h1 className="mt-6 text-3xl font-semibold">{signup ? "Create your account" : "Sign in"}</h1>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">
        {signup
          ? "Your account keeps the learner, the topic, and the session you resume."
          : "Continue the sessions saved to this account."}
      </p>
      {error ? (
        <div role="alert" className="mt-5 rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
          {error.requestId ? (
            <p className="mt-1 font-mono text-xs text-rose-800">Request ID: {error.requestId}</p>
          ) : null}
        </div>
      ) : null}
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {signup ? (
          <label className="block text-sm text-stone-700" htmlFor="display-name">
            Display name
            <input
              id="display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              autoComplete="name"
              maxLength={80}
              className="mt-1 w-full rounded border border-stone-300 bg-white px-3 py-2"
            />
          </label>
        ) : null}
        <label className="block text-sm text-stone-700" htmlFor="email">
          Email
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            maxLength={254}
            className="mt-1 w-full rounded border border-stone-300 bg-white px-3 py-2"
          />
        </label>
        <label className="block text-sm text-stone-700" htmlFor="password">
          Password
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={signup ? "new-password" : "current-password"}
            minLength={signup ? 8 : undefined}
            maxLength={72}
            className="mt-1 w-full rounded border border-stone-300 bg-white px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded bg-stone-950 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {pending ? "Saving…" : signup ? "Create account" : "Sign in"}
        </button>
      </form>
      <p className="mt-5 text-sm text-stone-600">
        {signup ? (
          <>
            Already have an account?{" "}
            <Link href="/signin" className="text-stone-950 underline">
              Sign in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href="/signup" className="text-stone-950 underline">
              Create an account
            </Link>
          </>
        )}
      </p>
    </main>
  );
}
