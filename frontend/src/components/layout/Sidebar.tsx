'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bot,
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  Wrench,
  Settings,
  Sparkles,
} from 'lucide-react';
import TenantSwitcher from './TenantSwitcher';

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'AI Employees', href: '/ai-employees', icon: Bot },
  {
    name: 'Knowledge Base',
    href: '/knowledge',
    icon: BookOpen,
    badge: 'Phase 1 RAG',
    badgeColor: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
  },
  {
    name: 'Conversations',
    href: '/conversations',
    icon: MessageSquare,
    badge: 'Phase 2 Chat',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  },
  {
    name: 'Settings & Team',
    href: '/settings',
    icon: Settings,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 min-h-screen">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="font-bold text-base text-white tracking-tight">
            AI Employee<span className="text-indigo-400">.OS</span>
          </div>
        </Link>

        {/* Tenant / Workspace Selector */}
        <div className="mt-4">
          <TenantSwitcher />
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800 text-xs text-slate-400">
        <div className="flex items-center gap-1.5 font-medium text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Phase 0 Foundation
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Multi-tenant core architecture active.
        </p>
      </div>
    </aside>
  );
}
