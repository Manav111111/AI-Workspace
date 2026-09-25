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
  BarChart3,
  FlaskConical,
  Activity,
  Coins,
  ShieldCheck,
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
    name: 'Playground',
    href: '/playground',
    icon: FlaskConical,
    badge: 'Phase 12',
    badgeColor: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  },
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
    name: 'Observability',
    href: '/observability',
    icon: Activity,
    badge: 'Phase 11',
    badgeColor: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
  },
  {
    name: 'Usage & Budgets',
    href: '/usage',
    icon: Coins,
    badge: 'Phase 13',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  },
  {
    name: 'RAG Evaluations',
    href: '/evaluations',
    icon: BarChart3,
    badge: 'Phase 8',
    badgeColor: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
  },
  {
    name: 'Audit Logs',
    href: '/audit',
    icon: ShieldCheck,
    badge: 'Gov',
    badgeColor: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
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
