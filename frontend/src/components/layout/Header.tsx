'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { User } from '@/types';
import { LogOut, User as UserIcon, Shield } from 'lucide-react';

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const res = await api.getMe();
        setUser(res.user);
      } catch (err) {
        // Not logged in or mock state
      }
    }
    loadUser();
  }, []);

  const handleLogout = () => {
    api.clearSession();
    router.push('/login');
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Tenant Isolation Active</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user ? (
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium text-slate-200">{user.full_name}</div>
              <div className="text-xs text-slate-400">{user.email}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Log out"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => router.push('/login')}
            className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}
