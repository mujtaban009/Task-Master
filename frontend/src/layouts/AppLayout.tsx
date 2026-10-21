import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  CheckSquare,
  LayoutDashboard,
  ShieldCheck,
  LogOut,
  Menu,
  X,
  BookOpen,
} from 'lucide-react';
import { ChatAssistantWidget } from '../components/ChatAssistantWidget';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAdmin, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/dashboard" className="flex items-center space-x-2">
                <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-sm">
                  <CheckSquare className="w-5 h-5" />
                </div>
                <span className="font-bold text-xl text-slate-900 tracking-tight">TaskMaster</span>
              </Link>

              {/* Desktop Nav Links */}
              <nav className="hidden md:ml-8 md:flex md:space-x-4">
                <Link
                  to="/dashboard"
                  className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/dashboard')
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4 mr-2" />
                  My Tasks
                </Link>

                {isAdmin && (
                  <Link
                    to="/admin"
                    className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive('/admin')
                        ? 'bg-purple-50 text-purple-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4 mr-2" />
                    Admin Panel
                  </Link>
                )}

                <Link
                  to="/blog"
                  className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/blog') || location.pathname.startsWith('/blog')
                      ? 'bg-emerald-50 text-emerald-700 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <BookOpen className="w-4 h-4 mr-2 text-emerald-600" />
                  Productivity Blog
                </Link>
              </nav>
            </div>

            {/* User profile dropdown & actions */}
            <div className="hidden md:flex md:items-center md:space-x-4">
              <div className="flex items-center space-x-3 text-sm">
                <div className="text-right">
                  <div className="font-semibold text-slate-800">{user?.full_name}</div>
                  <div className="text-xs text-slate-500 flex items-center justify-end space-x-1">
                    <span>{user?.email}</span>
                    {isAdmin && (
                      <span className="bg-purple-100 text-purple-800 text-[10px] font-semibold px-1.5 py-0.5 rounded">
                        Admin
                      </span>
                    )}
                  </div>
                </div>
                <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold border border-slate-300">
                  {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
                </div>
              </div>

              <button
                onClick={() => logout()}
                className="inline-flex items-center px-3 py-1.5 border border-slate-300 rounded-md text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 transition shadow-sm"
              >
                <LogOut className="w-4 h-4 mr-1.5 text-slate-500" />
                Logout
              </button>
            </div>

            {/* Mobile menu trigger */}
            <div className="flex items-center md:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="text-slate-600 hover:text-slate-900 p-2"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu panel */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-slate-200 bg-white px-4 pt-2 pb-3 space-y-1">
            <Link
              to="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-100"
            >
              My Tasks
            </Link>
            {isAdmin && (
              <Link
                to="/admin"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-purple-700 hover:bg-purple-50"
              >
                Admin Panel
              </Link>
            )}
            <Link
              to="/blog"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-base font-medium text-emerald-700 hover:bg-emerald-50"
            >
              Productivity Blog
            </Link>
            <div className="pt-4 pb-2 border-t border-slate-200">
              <div className="font-medium text-slate-800">{user?.full_name}</div>
              <div className="text-sm text-slate-500">{user?.email}</div>
              <button
                onClick={() => logout()}
                className="mt-3 w-full flex items-center justify-center px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 bg-white hover:bg-slate-50"
              >
                <LogOut className="w-4 h-4 mr-2 text-slate-500" />
                Logout
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        TaskMaster &bull; Production-Ready To-Do List Application &bull; Phase 3 React
      </footer>

      {/* Floating AI Assistant Chatbot Widget */}
      <ChatAssistantWidget />
    </div>
  );
};
