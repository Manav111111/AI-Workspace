'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { User } from '@/types';
import { LogOut, Shield, Terminal } from 'lucide-react';
import Link from 'next/link';

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const res = await api.getMe();
        setUser(res.user);
      } catch (err) {
        // Unauthenticated or mock state
      }
    }
    loadUser();
  }, []);

  const handleLogout = () => {
    api.clearSession();
    router.push('/login');
  };

  return (
    <header className="h-14 border-b border-[#262626] bg-[#080808]/90 backdrop-blur-md px-6 flex items-center justify-between shrink-0 z-30">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#101010] border border-[#262626] text-xs text-[#A1A1AA]">
          <Shield className="w-3.5 h-3.5 text-[#FF9D00]" />
          <span className="font-mono text-[11px] text-[#A1A1AA]">Tenant Boundary Enforced</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Link
          href="/playground"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#101010] hover:bg-[#151515] border border-[#262626] hover:border-[#383838] text-xs text-[#F5F5F5] transition-editorial"
        >
          <Terminal className="w-3.5 h-3.5 text-[#FF9D00]" />
          <span className="font-medium">Test in Playground</span>
        </Link>

        {user ? (
          <div className="flex items-center gap-3 border-l border-[#262626] pl-4">
            <div className="text-right">
              <div className="text-xs font-medium text-[#F5F5F5] tracking-tight">{user.full_name}</div>
              <div className="text-[10px] text-[#737373] font-mono">{user.email}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Log out"
              className="p-1.5 rounded-lg text-[#737373] hover:text-rose-400 hover:bg-[#151515] transition-editorial"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => router.push('/login')}
            className="text-xs font-semibold text-[#FF9D00] hover:text-[#FF6A00] transition-editorial"
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}

