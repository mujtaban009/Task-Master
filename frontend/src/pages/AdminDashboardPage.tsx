import React, { useState, useEffect } from 'react';
import { User, AdminDashboardStats } from '../types';
import { apiClient } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import {
  Users,
  CheckCircle2,
  ListTodo,
  Search,
  Shield,
  Activity,
} from 'lucide-react';

export const AdminDashboardPage: React.FC = () => {
  const { user: currentAdmin } = useAuth();
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [statsRes, usersRes] = await Promise.all([
        apiClient.get<AdminDashboardStats>('/admin/dashboard'),
        apiClient.get<User[]>('/admin/users', { params: { search: search.trim() || undefined } }),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      console.error('Failed to load admin dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, [search]);

  // Refresh system totals when the Admin Agent creates or assigns tasks
  useEffect(() => {
    window.addEventListener('tasks-changed', fetchAdminData);
    return () => window.removeEventListener('tasks-changed', fetchAdminData);
  }, [search]);

  const handleToggleUserStatus = async (user: User) => {
    if (user.id === currentAdmin?.id && user.is_active) {
      alert('Administrators cannot deactivate their own account.');
      return;
    }

    try {
      await apiClient.patch(`/admin/users/${user.id}/status`, {
        is_active: !user.is_active,
      });
      fetchAdminData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user status.');
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center">
          <Shield className="w-6 h-6 mr-2 text-purple-600" />
          Administrative Control Center
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Real-time system telemetry, cross-system metrics, and user management.
        </p>
      </div>

      {loading && !stats && (
        <div className="text-center py-8 text-slate-500 text-sm animate-pulse">
          Loading metrics...
        </div>
      )}

      {/* Cross-System Metrics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Users</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{stats.total_users}</h3>
              <p className="text-xs text-slate-500 mt-1">
                {stats.active_users} active &bull; {stats.inactive_users} inactive
              </p>
            </div>
            <div className="p-3 rounded-lg bg-purple-50 text-purple-600">
              <Users className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Tasks</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{stats.total_tasks}</h3>
              <p className="text-xs text-slate-500 mt-1">
                {stats.pending_tasks} pending &bull; {stats.in_progress_tasks} in-progress
              </p>
            </div>
            <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
              <ListTodo className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Completed Tasks</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{stats.completed_tasks}</h3>
              <p className="text-xs text-emerald-600 font-semibold mt-1">
                {stats.completion_rate_percentage}% Completion
              </p>
            </div>
            <div className="p-3 rounded-lg bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">System Status</p>
              <h3 className="text-2xl font-bold text-emerald-600 mt-1">Healthy</h3>
              <p className="text-xs text-slate-500 mt-1">PostgreSQL 18 Connected</p>
            </div>
            <div className="p-3 rounded-lg bg-emerald-50 text-emerald-600">
              <Activity className="w-5 h-5" />
            </div>
          </div>
        </div>
      )}

      {/* User Management Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-base font-bold text-slate-800">System Users</h2>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold text-xs uppercase">
              <tr>
                <th className="px-6 py-3">User</th>
                <th className="px-6 py-3">Role</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Joined Date</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50 transition">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-slate-900">{u.full_name}</div>
                    <div className="text-slate-500 text-xs">{u.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        u.role === 'admin'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Suspended'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-slate-500 text-xs">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => handleToggleUserStatus(u)}
                      disabled={u.id === currentAdmin?.id}
                      className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${
                        u.is_active
                          ? 'border-rose-300 text-rose-700 hover:bg-rose-50'
                          : 'border-emerald-300 text-emerald-700 hover:bg-emerald-50'
                      } disabled:opacity-30 disabled:cursor-not-allowed`}
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
