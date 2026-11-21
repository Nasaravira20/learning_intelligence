import Link from "next/link";

import { SiteHeader } from "@/components/SiteHeader";

const loop = [
  { step: "01", name: "Understand", text: "Take the topic the learner actually chose." },
  { step: "02", name: "Diagnose", text: "Find the gap before giving the next explanation." },
  { step: "03", name: "Plan", text: "Choose the next move from what the learner has shown." },
  { step: "04", name: "Teach", text: "Teach that move, then ask the learner to use it." },
  { step: "05", name: "Evaluate", text: "Score the attempt against the skill, not the chat." },
  { step: "06", name: "Adapt", text: "Change the next step when the evidence changes." },
  { step: "07", name: "Retain", text: "Bring the skill back later, and keep the record." },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#f4f0e8] text-stone-950">
      <SiteHeader />
      <main>
        <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-8 md:grid-cols-[1.3fr_0.7fr] md:items-end">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-amber-800">Teacher Mode</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
              From answer intelligence to learning intelligence.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-stone-700">
              MNEMO keeps a learner’s progress. It diagnoses a gap, teaches the next step, and
              checks whether that step held.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/signup" className="rounded bg-stone-950 px-5 py-3 text-sm text-[#f4f0e8]">
                Start learning
              </Link>
              <Link href="/signin" className="rounded border border-stone-400 px-5 py-3 text-sm">
                Sign in
              </Link>
            </div>
          </div>
          <aside className="rounded-2xl border border-stone-300 bg-[#efe8db] p-6">
            <p className="text-xs uppercase tracking-[0.16em] text-stone-500">What stays</p>
            <ul className="mt-4 space-y-3 text-sm leading-relaxed text-stone-800">
              <li>A named learner, not an anonymous chat.</li>
              <li>A topic, a session, and a saved status.</li>
              <li>A resume time you can come back to.</li>
            </ul>
          </aside>
        </section>

        <section className="border-y border-stone-300 bg-[#efe8db]">
          <div className="mx-auto max-w-6xl px-5 py-14">
            <h2 className="text-2xl font-semibold">The teaching loop</h2>
            <ol className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {loop.map((item) => (
                <li key={item.step} className="rounded-xl border border-stone-300 bg-[#f4f0e8] p-4">
                  <p className="font-mono text-xs text-amber-800">{item.step}</p>
                  <h3 className="mt-2 font-semibold">{item.name}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-stone-700">{item.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-4 px-5 py-14 md:grid-cols-3">
          <article className="rounded-2xl border border-stone-300 p-5">
            <h2 className="text-lg font-semibold">Diagnosis before explanation</h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              The next lesson follows the learner’s current gap. A correct-looking answer is not
              the same as a skill the learner can use again.
            </p>
          </article>
          <article className="rounded-2xl border border-stone-300 p-5">
            <h2 className="text-lg font-semibold">Evidence, then the next step</h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              Each session keeps what was chosen and what happened. Later phases score that
              evidence and change the plan.
            </p>
          </article>
          <article className="rounded-2xl border border-stone-300 p-5">
            <h2 className="text-lg font-semibold">Come back to the same work</h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              Sign in, open Teacher Mode, and resume the session. The record stays with the
              account.
            </p>
          </article>
        </section>
      </main>
      <footer className="border-t border-stone-300 px-5 py-6 text-sm text-stone-600">
        <div className="mx-auto flex max-w-6xl justify-between gap-4">
          <span>MNEMO</span>
          <span>Teacher Mode</span>
        </div>
      </footer>
    </div>
  );
}
