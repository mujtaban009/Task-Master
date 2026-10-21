import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  CheckSquare,
  Bot,
  ShieldCheck,
  Users,
  Sparkles,
  ArrowRight,
  ListChecks,
  Send,
  CheckCircle2,
  Circle,
  Clock,
} from 'lucide-react';

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Writes scroll progress (--p, 0..1 over the first screen) and pointer position (--mx/--my, -1..1)
 *  to CSS variables on the page root. CSS does all the 3D work; React never re-renders. */
function useMotionVars(rootRef: React.RefObject<HTMLDivElement>) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root || reducedMotion()) return;
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        root.style.setProperty('--p', Math.min(window.scrollY / window.innerHeight, 1).toFixed(3));
      });
    };
    const onPointer = (e: PointerEvent) => {
      root.style.setProperty('--mx', ((e.clientX / window.innerWidth) * 2 - 1).toFixed(3));
      root.style.setProperty('--my', ((e.clientY / window.innerHeight) * 2 - 1).toFixed(3));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointermove', onPointer, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pointermove', onPointer);
    };
  }, [rootRef]);
}

/** Adds .is-visible to [data-reveal] elements as they scroll into view (once). */
function useReveal(rootRef: React.RefObject<HTMLDivElement>) {
  useEffect(() => {
    const items = rootRef.current?.querySelectorAll('[data-reveal]') ?? [];
    if (reducedMotion() || !('IntersectionObserver' in window)) {
      items.forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        }),
      { threshold: 0.2 }
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [rootRef]);
}

/** Card that tilts toward the pointer while hovered. */
const TiltCard: React.FC<{ className?: string; children: React.ReactNode; style?: React.CSSProperties }> = ({
  className = '',
  children,
  style,
}) => {
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reducedMotion()) return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--tx', (((e.clientX - r.left) / r.width) * 2 - 1).toFixed(3));
    e.currentTarget.style.setProperty('--ty', (((e.clientY - r.top) / r.height) * 2 - 1).toFixed(3));
  };
  const onLeave = (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.style.setProperty('--tx', '0');
    e.currentTarget.style.setProperty('--ty', '0');
  };
  return (
    <div className={`lp-tilt ${className}`} style={style} onPointerMove={onMove} onPointerLeave={onLeave}>
      {children}
    </div>
  );
};

const boardTasks = [
  { title: 'Design onboarding flow', tag: 'High', done: true },
  { title: 'Review API security', tag: 'High', done: false },
  { title: 'Prepare sprint demo', tag: 'Medium', done: false },
  { title: 'Write release notes', tag: 'Low', done: false },
];

const features = [
  {
    icon: Bot,
    title: 'An AI assistant that gets things done',
    text: 'Ask anything, hold a real conversation, and add several tasks from one message. It reads only your own data.',
    accent: 'from-emerald-400 to-teal-500',
  },
  {
    icon: Users,
    title: 'Admins plan and assign in seconds',
    text: 'The admin agent sees every user and task, turns plans into tasks, and assigns work with one sentence.',
    accent: 'from-violet-400 to-fuchsia-500',
  },
  {
    icon: ShieldCheck,
    title: 'Private and secure by design',
    text: 'Per-user data isolation, account lockout, single-use login tokens and email codes for password resets.',
    accent: 'from-sky-400 to-indigo-500',
  },
];

const steps = [
  { icon: Sparkles, title: 'Sign up free', text: 'Create your account in under a minute.' },
  { icon: ListChecks, title: 'Add your work', text: 'Type tasks or tell the assistant: "add A, B and C".' },
  { icon: CheckCircle2, title: 'Finish faster', text: 'Track progress, deadlines and priorities in one place.' },
];

export const LandingPage: React.FC = () => {
  const rootRef = useRef<HTMLDivElement>(null);
  const { isAuthenticated, isAdmin } = useAuth();
  useMotionVars(rootRef);
  useReveal(rootRef);

  return (
    <div ref={rootRef} className="lp-root min-h-screen overflow-x-clip bg-slate-950 text-white">
      {/* Floating depth layers: each moves at its own speed */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="lp-blob lp-blob-1" />
        <div className="lp-blob lp-blob-2" />
        <div className="lp-blob lp-blob-3" />
        <div className="lp-grid" />
      </div>

      {/* Top bar: auth actions in the top-right corner */}
      <header className="fixed inset-x-0 top-0 z-30 border-b border-white/10 bg-slate-950/70 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-bold tracking-tight">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/30">
              <CheckSquare className="h-5 w-5" />
            </span>
            TaskMaster
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            {isAuthenticated ? (
              <Link to={isAdmin ? '/admin' : '/dashboard'} className="lp-btn-primary">
                Open dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link to="/login" className="rounded-xl px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10 hover:text-white sm:px-4">
                  Log in
                </Link>
                <Link to="/register" className="lp-btn-primary">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className="relative z-10">
        {/* Hero */}
        <section className="lp-hero mx-auto grid min-h-screen max-w-7xl items-center gap-12 px-4 pb-16 pt-28 sm:px-6 lg:grid-cols-2">
          <div className="lp-hero-copy">
            <p className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-200">
              <Sparkles className="h-4 w-4" /> AI-powered task management
            </p>
            <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Plan less.{' '}
              <span className="bg-gradient-to-r from-emerald-300 via-teal-200 to-violet-300 bg-clip-text text-transparent">
                Get more done.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
              TaskMaster combines a clean to-do board with an AI assistant that talks with you, adds tasks for you
              and keeps your work private. Admins assign work to the whole team in one sentence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={isAuthenticated ? (isAdmin ? '/admin' : '/dashboard') : '/register'} className="lp-btn-primary lp-btn-lg">
                {isAuthenticated ? 'Open dashboard' : 'Start free'} <ArrowRight className="h-5 w-5" />
              </Link>
              <a href="#features" className="lp-btn-ghost lp-btn-lg">
                See how it works
              </a>
            </div>
          </div>

          {/* 3D board: tilts with the pointer, lays flat as you scroll */}
          <div className="lp-stage" aria-hidden="true">
            <div className="lp-board">
              <div className="lp-board-card lp-layer-0">
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <span className="font-semibold">My Tasks</span>
                  <span className="rounded-full bg-emerald-400/15 px-2 py-0.5 text-xs text-emerald-200">4 active</span>
                </div>
                <ul className="mt-3 space-y-2">
                  {boardTasks.map((t) => (
                    <li key={t.title} className="flex items-center gap-3 rounded-xl bg-white/5 px-3 py-2.5">
                      {t.done ? (
                        <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                      ) : (
                        <Circle className="h-5 w-5 shrink-0 text-slate-500" />
                      )}
                      <span className={`flex-1 text-sm ${t.done ? 'text-slate-500 line-through' : 'text-slate-100'}`}>{t.title}</span>
                      <span className={`rounded-md px-2 py-0.5 text-xs ${t.tag === 'High' ? 'bg-rose-400/15 text-rose-200' : t.tag === 'Medium' ? 'bg-amber-400/15 text-amber-200' : 'bg-slate-400/15 text-slate-300'}`}>
                        {t.tag}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="lp-board-chat lp-layer-1">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <span className="lp-orb h-7 w-7" /> My Assistant
                </div>
                <p className="mt-3 rounded-2xl rounded-br-md bg-gradient-to-br from-emerald-500 to-emerald-700 px-3 py-2 text-sm">
                  Add tasks: book flights, pack, renew passport
                </p>
                <p className="mt-2 rounded-2xl rounded-bl-md bg-white/10 px-3 py-2 text-sm text-slate-200">
                  Added 3 tasks ✓
                </p>
                <div className="mt-3 flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs text-slate-400">
                  Ask anything… <Send className="ml-auto h-3.5 w-3.5" />
                </div>
              </div>

              <div className="lp-board-chip lp-layer-2">
                <Clock className="h-4 w-4 text-violet-300" /> Due today: 2
              </div>
            </div>
          </div>
        </section>

        {/* Features: rise into place in 3D, tilt under the pointer */}
        <section id="features" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-24 sm:px-6">
          <div data-reveal className="lp-reveal mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Everything your team needs, nothing it doesn't</h2>
            <p className="mt-4 text-slate-300">Built for individuals and teams who want clarity without the clutter.</p>
          </div>
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {features.map((f, i) => (
              <div key={f.title} data-reveal className="lp-reveal lp-reveal-3d" style={{ transitionDelay: `${i * 120}ms` }}>
                <TiltCard className="h-full rounded-3xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur">
                  <span className={`lp-icon-3d inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${f.accent}`}>
                    <f.icon className="h-6 w-6" />
                  </span>
                  <h3 className="mt-5 text-xl font-semibold">{f.title}</h3>
                  <p className="mt-3 leading-relaxed text-slate-300">{f.text}</p>
                </TiltCard>
              </div>
            ))}
          </div>
        </section>

        {/* Steps: each card flips up as it enters */}
        <section className="mx-auto max-w-5xl px-4 py-24 sm:px-6">
          <h2 data-reveal className="lp-reveal text-center text-3xl font-bold tracking-tight sm:text-4xl">
            Up and running in three steps
          </h2>
          <ol className="mt-14 grid gap-6 md:grid-cols-3">
            {steps.map((s, i) => (
              <li key={s.title} data-reveal className="lp-reveal lp-flip" style={{ transitionDelay: `${i * 150}ms` }}>
                <div className="relative h-full rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.07] to-white/[0.02] p-6">
                  <span className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-violet-500 text-sm font-bold shadow-lg">
                    {i + 1}
                  </span>
                  <s.icon className="mt-2 h-7 w-7 text-emerald-300" />
                  <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                  <p className="mt-2 text-slate-300">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Final call to action */}
        <section className="mx-auto max-w-5xl px-4 pb-28 pt-8 sm:px-6">
          <div data-reveal className="lp-reveal lp-reveal-3d">
            <TiltCard className="overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-emerald-500/20 via-slate-900 to-violet-500/20 p-10 text-center sm:p-14">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Ready to clear your list?</h2>
              <p className="mx-auto mt-4 max-w-xl text-slate-300">Free to use. Your tasks stay private to you.</p>
              <Link to={isAuthenticated ? (isAdmin ? '/admin' : '/dashboard') : '/register'} className="lp-btn-primary lp-btn-lg mt-8">
                {isAuthenticated ? 'Open dashboard' : 'Create your free account'} <ArrowRight className="h-5 w-5" />
              </Link>
            </TiltCard>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/10 py-8 text-center text-sm text-slate-400">
        © {new Date().getFullYear()} TaskMaster
      </footer>
    </div>
  );
};
