import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { CheckSquare, Lock, Mail, KeyRound, AlertCircle, CheckCircle2 } from 'lucide-react';

type Step = 'email' | 'code' | 'done';

const inputClass =
  'block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm';
const buttonClass =
  'w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition';

export const ForgotPasswordPage: React.FC = () => {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const requestCode = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient.post<{ detail: string }>('/auth/forgot-password', { email });
      setInfo(`${res.data.detail} Check your inbox and spam folder.`);
      setStep('code');
    } catch (err: any) {
      setError(err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || 'Could not send the code. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError('The two passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await apiClient.post('/auth/reset-password', { email, code, new_password: newPassword });
      setStep('done');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Use the 6-digit code and a password of at least 8 characters.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-md">
            <CheckSquare className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-3xl font-extrabold text-slate-900 tracking-tight">Reset your password</h2>
        <p className="mt-2 text-center text-sm text-slate-600">
          Remembered it?{' '}
          <Link to="/login" className="font-medium text-emerald-600 hover:text-emerald-500">
            Back to sign in
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm sm:rounded-xl sm:px-10 border border-slate-200">
          {error && (
            <div role="alert" className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center text-sm">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === 'email' && (
            <form className="space-y-6" onSubmit={requestCode}>
              <p className="text-sm text-slate-600">Enter your account email and we'll send you a 6-digit code.</p>
              <div>
                <label htmlFor="reset-email" className="block text-sm font-medium text-slate-700">Email address</label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400" />
                  </div>
                  <input id="reset-email" type="email" required autoComplete="email" value={email}
                    onChange={(e) => setEmail(e.target.value)} className={inputClass} placeholder="you@example.com" />
                </div>
              </div>
              <button type="submit" disabled={loading} className={buttonClass}>
                {loading ? 'Sending code...' : 'Send reset code'}
              </button>
            </form>
          )}

          {step === 'code' && (
            <form className="space-y-6" onSubmit={resetPassword}>
              {info && <p className="text-sm text-slate-600">{info}</p>}
              <div>
                <label htmlFor="reset-code" className="block text-sm font-medium text-slate-700">6-digit code</label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <KeyRound className="h-5 w-5 text-slate-400" />
                  </div>
                  <input id="reset-code" required inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}"
                    maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    className={`${inputClass} tracking-[0.4em] font-mono`} placeholder="123456" />
                </div>
              </div>
              <div>
                <label htmlFor="new-password" className="block text-sm font-medium text-slate-700">New password</label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input id="new-password" type="password" required minLength={8} autoComplete="new-password"
                    value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputClass}
                    placeholder="At least 8 characters" />
                </div>
              </div>
              <div>
                <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700">Confirm new password</label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input id="confirm-password" type="password" required minLength={8} autoComplete="new-password"
                    value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputClass} />
                </div>
              </div>
              <button type="submit" disabled={loading} className={buttonClass}>
                {loading ? 'Updating...' : 'Set new password'}
              </button>
              <button type="button" onClick={() => requestCode()} disabled={loading}
                className="w-full text-sm font-medium text-emerald-600 hover:text-emerald-500 disabled:opacity-50">
                Didn't get it? Send a new code
              </button>
            </form>
          )}

          {step === 'done' && (
            <div className="text-center space-y-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
              <p className="text-sm text-slate-700">
                Your password was changed and you were signed out everywhere. Sign in with your new password.
              </p>
              <Link to="/login" className={buttonClass}>Go to sign in</Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
