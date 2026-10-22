import React from 'react';
import { Link } from 'react-router-dom';
import { CheckSquare } from 'lucide-react';

/** Shared frame for the login, register and forgot-password pages: animated light background,
 *  clickable TaskMaster brand (goes to the landing page), title and a glass card. */
export const AuthShell: React.FC<{ title: string; subtitle: React.ReactNode; children: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <div className="auth-root relative min-h-screen overflow-hidden bg-[#04060a] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    {/* Dark moving background: glowing color blobs, dot grid and a bright clock dial */}
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />
      <div className="auth-blob auth-blob-3" />
      <div className="auth-dots" />
      <svg viewBox="0 0 400 400" className="auth-clock">
        <circle cx="200" cy="200" r="190" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="200" cy="200" r="150" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 7" />
        {Array.from({ length: 60 }, (_, i) => (
          <line key={i} x1="200" y1="14" x2="200" y2={i % 5 === 0 ? 36 : 24} stroke="currentColor" strokeWidth={i % 5 === 0 ? 2 : 1}
            transform={`rotate(${i * 6} 200 200)`} />
        ))}
        <g className="auth-hand">
          <line x1="200" y1="200" x2="200" y2="48" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </g>
        <circle cx="200" cy="200" r="6" fill="currentColor" />
      </svg>
    </div>

    <div className="relative sm:mx-auto sm:w-full sm:max-w-md">
      <div className="auth-rise flex justify-center" style={{ animationDelay: '0ms' }}>
        <Link
          to="/"
          aria-label="TaskMaster home"
          className="group inline-flex items-center gap-2.5 rounded-xl px-2 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-500"
        >
          <span className="auth-logo flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-lg shadow-emerald-500/30 transition-transform duration-300 group-hover:rotate-6 group-hover:scale-110">
            <CheckSquare className="h-6 w-6" />
          </span>
          <span className="text-2xl font-extrabold tracking-tight text-white transition-colors group-hover:text-emerald-300">
            TaskMaster
          </span>
        </Link>
      </div>
      <h2 className="auth-rise mt-6 text-center text-3xl font-extrabold text-white tracking-tight" style={{ animationDelay: '90ms' }}>
        {title}
      </h2>
      <p className="auth-rise mt-2 text-center text-sm text-slate-300 [&_a]:text-emerald-400 [&_a:hover]:text-emerald-300" style={{ animationDelay: '150ms' }}>
        {subtitle}
      </p>
    </div>

    <div className="relative mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      {/* The form panel keeps the original light design */}
      <div className="auth-card auth-rise bg-white py-8 px-4 shadow-sm sm:rounded-xl sm:px-10 border border-slate-200" style={{ animationDelay: '220ms' }}>
        {children}
      </div>
    </div>
  </div>
);
