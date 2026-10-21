import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { BLOG_POSTS } from '../data/blogPosts';
import {
  CheckSquare,
  Clock,
  ArrowRight,
  Search,
  BookOpen,
  Sparkles,
  TrendingUp,
  Tag,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const BlogPage: React.FC = () => {
  const { isAuthenticated, isAdmin } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  // Categories list
  const categories = ['All', 'Success & Mindset', 'Frameworks & Systems', 'TaskMaster Guides'];

  // Filter posts based on search query and category
  const filteredPosts = useMemo(() => {
    return BLOG_POSTS.filter((post) => {
      const matchesSearch =
        post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        post.excerpt.toLowerCase().includes(searchQuery.toLowerCase()) ||
        post.keywords.some((k) => k.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesCategory =
        selectedCategory === 'All' || post.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory]);

  const featuredPost = BLOG_POSTS[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* Dynamic SEO Meta Header */}
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
              to="/"
              className="text-sm font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg transition hover:bg-white/5 hidden sm:inline-block"
            >
              Home
            </Link>
            {isAuthenticated ? (
              <Link
                to={isAdmin ? '/admin' : '/dashboard'}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 transition"
              >
                Dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="rounded-xl px-3 py-2 text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white transition"
                >
                  Log in
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 transition"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 pt-24 pb-20">
        {/* Hero Section */}
        <section className="relative overflow-hidden px-4 py-16 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          {/* Subtle background glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-sm font-medium text-emerald-300 mb-6">
              <BookOpen className="h-4 w-4" /> The TaskMaster Productivity & Time Mastery Journal
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-white">
              Master Your Time.{' '}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                Unlock Unstoppable Success.
              </span>
            </h1>
            <p className="mt-6 text-lg text-slate-300 leading-relaxed">
              Explore evidence-based frameworks, neuroscience insights, and actionable strategies to
              eliminate procrastination, protect deep work, and achieve 10x life velocity with TaskMaster.
            </p>

            {/* Search Bar & Category Filters */}
            <div className="mt-10 max-w-xl mx-auto">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search articles on time management, GTD, productivity..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-slate-900 border border-white/10 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition shadow-inner"
                />
              </div>

              {/* Category Pills */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition ${
                      selectedCategory === cat
                        ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/25'
                        : 'bg-slate-900 border border-white/10 text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Featured Post Banner (Only when All category and no active search) */}
        {selectedCategory === 'All' && !searchQuery && (
          <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
            <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900/90 to-emerald-950/40 p-8 sm:p-12 shadow-2xl">
              <div className="grid lg:grid-cols-12 gap-8 items-center">
                <div className="lg:col-span-7">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 text-xs font-bold uppercase tracking-wider">
                      Featured Pillar Article
                    </span>
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> {featuredPost.readTime}
                    </span>
                  </div>

                  <Link to={`/blog/${featuredPost.slug}`}>
                    <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white hover:text-emerald-300 transition-colors leading-tight">
                      {featuredPost.title}
                    </h2>
                  </Link>

                  <p className="mt-4 text-slate-300 leading-relaxed text-sm sm:text-base">
                    {featuredPost.excerpt}
                  </p>

                  <div className="mt-6 flex items-center justify-between flex-wrap gap-4 pt-6 border-t border-white/10">
                    <div className="flex items-center gap-3">
                      <img
                        src={featuredPost.author.avatar}
                        alt={featuredPost.author.name}
                        className="w-10 h-10 rounded-full object-cover ring-2 ring-emerald-500/50"
                      />
                      <div>
                        <div className="text-sm font-semibold text-white">{featuredPost.author.name}</div>
                        <div className="text-xs text-slate-400">{featuredPost.author.role}</div>
                      </div>
                    </div>

                    <Link
                      to={`/blog/${featuredPost.slug}`}
                      className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-400 hover:text-emerald-300 group transition"
                    >
                      Read Full Article <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </Link>
                  </div>
                </div>

                <div className="lg:col-span-5">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-6 shadow-xl backdrop-blur-sm">
                    <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">
                      Article Key Insights:
                    </div>
                    <ul className="space-y-3 text-sm text-slate-300">
                      {featuredPost.content.takeaways.map((t, idx) => (
                        <li key={idx} className="flex items-start gap-2.5">
                          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold mt-0.5">
                            ✓
                          </span>
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Blog Posts Grid */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/10">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-emerald-400" />
              Latest Articles ({filteredPosts.length})
            </h2>
            {selectedCategory !== 'All' && (
              <span className="text-sm text-slate-400">
                Filtered by <strong className="text-emerald-300">{selectedCategory}</strong>
              </span>
            )}
          </div>

          {filteredPosts.length === 0 ? (
            <div className="text-center py-20 rounded-3xl border border-white/10 bg-slate-900/50">
              <Search className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white">No matching articles found</h3>
              <p className="text-slate-400 mt-2 max-w-md mx-auto">
                Try searching for a different keyword or resetting your category filter.
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('All');
                }}
                className="mt-6 px-4 py-2 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-500 transition text-sm"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {filteredPosts.map((post) => (
                <article
                  key={post.id}
                  className="flex flex-col justify-between rounded-3xl border border-white/10 bg-slate-900/60 p-6 hover:border-emerald-500/40 hover:bg-slate-900/90 transition-all duration-300 hover:shadow-2xl hover:shadow-emerald-500/10 group"
                >
                  <div>
                    {/* Category & Read Time */}
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {post.category}
                      </span>
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" /> {post.readTime}
                      </span>
                    </div>

                    {/* Article Title */}
                    <Link to={`/blog/${post.slug}`}>
                      <h3 className="text-xl font-bold text-white group-hover:text-emerald-300 transition-colors line-clamp-2 leading-snug">
                        {post.title}
                      </h3>
                    </Link>

                    {/* Excerpt */}
                    <p className="mt-3 text-sm text-slate-400 line-clamp-3 leading-relaxed">
                      {post.excerpt}
                    </p>

                    {/* Keywords pills */}
                    <div className="flex flex-wrap gap-1.5 mt-4">
                      {post.keywords.slice(0, 3).map((kw, i) => (
                        <span key={i} className="text-[11px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-md flex items-center gap-1">
                          <Tag className="w-2.5 h-2.5 text-emerald-400" /> {kw}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Author & Action footer */}
                  <div className="mt-8 pt-4 border-t border-white/10 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <img
                        src={post.author.avatar}
                        alt={post.author.name}
                        className="w-8 h-8 rounded-full object-cover ring-1 ring-emerald-500/30"
                      />
                      <div className="text-xs">
                        <div className="font-semibold text-slate-200">{post.author.name}</div>
                        <div className="text-slate-400 text-[11px]">{post.publishedDate}</div>
                      </div>
                    </div>

                    <Link
                      to={`/blog/${post.slug}`}
                      className="p-2 rounded-xl bg-white/5 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-all shadow-sm"
                      aria-label={`Read ${post.title}`}
                    >
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* High Conversion Call to Action Banner */}
        <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 mt-24">
          <div className="relative overflow-hidden rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-600/20 via-slate-900 to-teal-900/30 p-8 sm:p-14 text-center shadow-2xl backdrop-blur-md">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300 mb-4">
              <TrendingUp className="h-4 w-4" /> Elevate Your Life Architecture
            </span>
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl tracking-tight">
              Ready to Turn Time into Your Greatest Competitive Edge?
            </h2>
            <p className="mt-4 text-slate-300 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
              TaskMaster provides the distraction-free structure, priority clarity, and intelligent AI assistant
              you need to reclaim your focus and fulfill your highest potential.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-3.5 text-base font-semibold text-white shadow-xl shadow-emerald-500/25 hover:from-emerald-400 hover:to-teal-500 transition"
              >
                Create Your Free Account <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                to="/login"
                className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl bg-slate-900 border border-white/10 px-6 py-3.5 text-base font-semibold text-slate-200 hover:bg-slate-800 hover:text-white transition"
              >
                Log In to Existing Workspace
              </Link>
            </div>
          </div>
        </section>
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
