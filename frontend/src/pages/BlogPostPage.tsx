import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { BLOG_POSTS } from '../data/blogPosts';
import {
  CheckSquare,
  Clock,
  Calendar,
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  HelpCircle,
  ChevronDown,
  Sparkles,
  BookOpen,
  Copy,
  Check,
  Twitter,
  Linkedin,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const BlogPostPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { isAuthenticated, isAdmin } = useAuth();
  const [copied, setCopied] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const post = BLOG_POSTS.find((p) => p.slug === slug);

  // SEO: Update Title, Meta tags, and Structured Data
  useEffect(() => {
    if (post) {
      document.title = `${post.title} | TaskMaster Productivity Blog`;

      // Update or create meta description
      let metaDesc = document.querySelector('meta[name="description"]');
      if (!metaDesc) {
        metaDesc = document.createElement('meta');
        metaDesc.setAttribute('name', 'description');
        document.head.appendChild(metaDesc);
      }
      metaDesc.setAttribute('content', post.metaDescription);

      // JSON-LD Structured Data for Google Rich Snippets
      const schemaData = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: post.title,
        description: post.metaDescription,
        datePublished: post.publishedDate,
        author: {
          '@type': 'Person',
          name: post.author.name,
          jobTitle: post.author.role,
        },
        publisher: {
          '@type': 'Organization',
          name: 'TaskMaster',
          logo: {
            '@type': 'ImageObject',
            url: 'https://taskmaster.app/logo.png',
          },
        },
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': window.location.href,
        },
        keywords: post.keywords.join(', '),
      };

      const scriptId = 'jsonld-blog-post';
      let existingScript = document.getElementById(scriptId);
      if (!existingScript) {
        existingScript = document.createElement('script');
        existingScript.id = scriptId;
        existingScript.setAttribute('type', 'application/ld+json');
        document.head.appendChild(existingScript);
      }
      existingScript.textContent = JSON.stringify(schemaData);

      // Scroll to top upon navigation
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    return () => {
      const script = document.getElementById('jsonld-blog-post');
      if (script) script.remove();
    };
  }, [post]);

  if (!post) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4">
        <h1 className="text-3xl font-bold mb-4">Article Not Found</h1>
        <p className="text-slate-400 mb-6">The productivity guide you are looking for has been moved or updated.</p>
        <Link
          to="/blog"
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 font-semibold text-white hover:bg-emerald-500 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Blog Directory
        </Link>
      </div>
    );
  }

  // Related articles (the other two articles)
  const relatedPosts = BLOG_POSTS.filter((p) => p.id !== post.id).slice(0, 2);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* Navigation Header */}
      <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-slate-950/80 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-bold tracking-tight text-white hover:opacity-90 transition">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/30">
              <CheckSquare className="h-5 w-5 text-white" />
            </span>
            <span className="text-xl">TaskMaster</span>
            <span className="ml-2 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
              Blog
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <Link
              to="/blog"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg transition hover:bg-white/5"
            >
              <ArrowLeft className="w-4 h-4" /> All Articles
            </Link>
            {isAuthenticated ? (
              <Link
                to={isAdmin ? '/admin' : '/dashboard'}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 transition"
              >
                Dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <Link
                to="/register"
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 transition"
              >
                Start Free
              </Link>
            )}
          </div>
        </nav>
      </header>

      {/* Main Blog Article Container */}
      <main className="flex-1 pt-24 pb-20">
        <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Breadcrumb Navigation */}
          <nav aria-label="Breadcrumb" className="mb-6 flex items-center gap-2 text-xs text-slate-400">
            <Link to="/" className="hover:text-emerald-400 transition">Home</Link>
            <span>/</span>
            <Link to="/blog" className="hover:text-emerald-400 transition">Blog</Link>
            <span>/</span>
            <span className="text-slate-300 truncate max-w-xs">{post.category}</span>
          </nav>

          {/* Article Header */}
          <header className="mb-10 pb-8 border-b border-white/10">
            <div className="flex items-center gap-3 mb-4">
              <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 text-xs font-bold uppercase tracking-wider">
                {post.category}
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-emerald-400" /> {post.readTime}
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> {post.publishedDate}
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight">
              {post.title}
            </h1>

            <p className="mt-6 text-lg sm:text-xl text-slate-300 leading-relaxed font-normal">
              {post.excerpt}
            </p>

            {/* Author Profile and Social Sharing */}
            <div className="mt-8 flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-white/10">
              <div className="flex items-center gap-3.5">
                <img
                  src={post.author.avatar}
                  alt={post.author.name}
                  className="w-12 h-12 rounded-full object-cover ring-2 ring-emerald-500/40"
                />
                <div>
                  <div className="text-sm font-semibold text-white">{post.author.name}</div>
                  <div className="text-xs text-slate-400">{post.author.role}</div>
                </div>
              </div>

              {/* Share Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyLink}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition shadow-sm"
                  title="Copy Article Link"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied Link!' : 'Share'}
                </button>
                <a
                  href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(post.title)}&url=${encodeURIComponent(window.location.href)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-slate-900 border border-white/10 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 transition"
                  title="Share on X (Twitter)"
                >
                  <Twitter className="w-4 h-4" />
                </a>
                <a
                  href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.href)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-slate-900 border border-white/10 text-slate-300 hover:text-blue-400 hover:bg-slate-800 transition"
                  title="Share on LinkedIn"
                >
                  <Linkedin className="w-4 h-4" />
                </a>
              </div>
            </div>
          </header>

          {/* Article Lead / Introduction */}
          <div className="prose prose-invert max-w-none mb-12">
            <p className="text-lg leading-relaxed text-slate-200 bg-slate-900/40 border-l-4 border-emerald-500 p-5 rounded-r-2xl italic">
              "{post.content.introduction}"
            </p>
          </div>

          {/* Detailed Content Sections */}
          <div className="space-y-12">
            {post.content.sections.map((section) => (
              <section key={section.id} id={section.id} className="scroll-mt-24">
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-4 flex items-center gap-2">
                  <span className="w-2 h-6 bg-emerald-500 rounded-full inline-block" />
                  {section.title}
                </h2>

                <div className="space-y-4 text-slate-300 leading-relaxed text-base sm:text-lg">
                  {section.body.map((p, idx) => (
                    <p key={idx}>{p}</p>
                  ))}
                </div>

                {/* Callout box if present */}
                {section.callout && (
                  <div
                    className={`my-6 p-5 rounded-2xl border ${
                      section.callout.type === 'tip'
                        ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                        : section.callout.type === 'quote'
                        ? 'bg-slate-900/80 border-cyan-500/40 text-cyan-200'
                        : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" />
                      <div>
                        <div className="font-medium">{section.callout.text}</div>
                        {section.callout.author && (
                          <div className="text-xs mt-2 text-slate-400">— {section.callout.author}</div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Bullet Points if present */}
                {section.bulletPoints && (
                  <ul className="mt-4 space-y-2.5">
                    {section.bulletPoints.map((bp, bidx) => (
                      <li key={bidx} className="flex items-start gap-3 text-slate-300">
                        <span className="flex-shrink-0 w-2 h-2 rounded-full bg-emerald-400 mt-2.5" />
                        <span className="leading-relaxed">{bp}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Additional body paragraphs after callout/bullets */}
                {section.bodyContinuation && (
                  <div className="mt-4 space-y-4 text-slate-300 leading-relaxed text-base sm:text-lg">
                    {section.bodyContinuation.map((cp, cidx) => (
                      <p key={cidx}>{cp}</p>
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>

          {/* Key Takeaways Card */}
          <div className="mt-14 rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/40 to-slate-900 p-8 shadow-xl">
            <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
              Executive Key Takeaways
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {post.content.takeaways.map((takeaway, idx) => (
                <div key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/50 border border-white/5">
                  <span className="text-emerald-400 font-bold text-sm">0{idx + 1}.</span>
                  <span className="text-sm text-slate-300">{takeaway}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Frequently Asked Questions (FAQ) Section */}
          <section className="mt-16 pt-10 border-t border-white/10">
            <div className="flex items-center gap-2 mb-6">
              <HelpCircle className="w-6 h-6 text-emerald-400" />
              <h2 className="text-2xl font-bold text-white">Frequently Asked Questions</h2>
            </div>
            <p className="text-slate-400 text-sm mb-6">
              Common questions answered by performance coaches and the TaskMaster team.
            </p>

            <div className="space-y-4">
              {post.content.faqs.map((faq, idx) => {
                const isOpen = openFaq === idx;
                return (
                  <div
                    key={idx}
                    className="rounded-2xl border border-white/10 bg-slate-900/60 overflow-hidden transition"
                  >
                    <button
                      onClick={() => setOpenFaq(isOpen ? null : idx)}
                      className="w-full flex items-center justify-between p-5 text-left font-semibold text-white hover:text-emerald-300 transition"
                    >
                      <span className="text-base">{faq.question}</span>
                      <ChevronDown
                        className={`w-5 h-5 text-slate-400 transition-transform ${
                          isOpen ? 'rotate-180 text-emerald-400' : ''
                        }`}
                      />
                    </button>
                    {isOpen && (
                      <div className="px-5 pb-5 pt-1 text-sm text-slate-300 leading-relaxed border-t border-white/5 bg-slate-950/40">
                        {faq.answer}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Mid-Article Conversion Callout to TaskMaster */}
          <section className="mt-16 rounded-3xl border border-emerald-500/40 bg-gradient-to-r from-emerald-600/30 via-slate-900 to-teal-900/40 p-8 sm:p-10 text-center shadow-2xl">
            <h3 className="text-2xl font-bold text-white">
              Turn These Principles Into Instant Reality With TaskMaster
            </h3>
            <p className="mt-3 text-slate-300 max-w-xl mx-auto text-sm sm:text-base leading-relaxed">
              Don't leave your time to chance. Join thousands of focused achievers who organize their tasks,
              eliminate decision fatigue, and plan with AI on TaskMaster.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link
                to="/register"
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-6 py-3 text-sm shadow-lg shadow-emerald-500/30 transition"
              >
                Create Free Account <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/blog"
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 border border-white/10 hover:bg-slate-800 text-slate-200 font-semibold px-5 py-3 text-sm transition"
              >
                Explore More Articles
              </Link>
            </div>
          </section>

          {/* Related Articles Section */}
          <section className="mt-20 pt-10 border-t border-white/10">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-emerald-400" />
              Related Productivity Guides
            </h3>
            <div className="grid sm:grid-cols-2 gap-6">
              {relatedPosts.map((rel) => (
                <Link
                  key={rel.id}
                  to={`/blog/${rel.slug}`}
                  className="p-5 rounded-2xl border border-white/10 bg-slate-900/60 hover:bg-slate-900 hover:border-emerald-500/40 transition group"
                >
                  <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                    {rel.category}
                  </div>
                  <h4 className="font-bold text-white text-base group-hover:text-emerald-300 transition-colors line-clamp-2">
                    {rel.title}
                  </h4>
                  <p className="mt-2 text-xs text-slate-400 line-clamp-2">{rel.excerpt}</p>
                  <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                    <span>{rel.readTime}</span>
                    <span className="text-emerald-400 font-medium group-hover:translate-x-1 transition-transform flex items-center gap-1">
                      Read <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </article>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-10 bg-slate-950 text-slate-400 text-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-emerald-500" />
            <span className="font-bold text-white">TaskMaster</span>
            <span>— The AI-Powered Time Management Platform</span>
          </div>
          <div className="flex items-center gap-6">
            <Link to="/" className="hover:text-white transition">Home</Link>
            <Link to="/blog" className="hover:text-white transition text-emerald-400 font-semibold">Blog</Link>
            <Link to="/login" className="hover:text-white transition">Log In</Link>
            <Link to="/register" className="hover:text-white transition">Sign Up</Link>
          </div>
          <div>© {new Date().getFullYear()} TaskMaster. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
};
