'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bot,
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  Settings,
  BarChart3,
  FlaskConical,
  Activity,
  Coins,
  ShieldCheck,
  ChevronRight,
  Command,
} from 'lucide-react';
import TenantSwitcher from './TenantSwitcher';
import Logo from '@/components/brand/Logo';

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeVariant?: 'orange' | 'forest' | 'amber' | 'sand' | 'neutral';
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Workspace',
    items: [
      { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
      { name: 'AI Employees', href: '/ai-employees', icon: Bot },
      { name: 'Knowledge Base', href: '/knowledge', icon: BookOpen },
      { name: 'Conversations', href: '/conversations', icon: MessageSquare },
    ],
  },
  {
    label: 'Build & Test',
    items: [
      { name: 'Playground', href: '/playground', icon: FlaskConical, badge: 'Live', badgeVariant: 'orange' },
      { name: 'RAG Evaluations', href: '/evaluations', icon: BarChart3, badge: 'Benchmark', badgeVariant: 'orange' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { name: 'Observability', href: '/observability', icon: Activity, badge: 'OTel', badgeVariant: 'neutral' },
      { name: 'Usage & Budgets', href: '/usage', icon: Coins, badge: 'Cost', badgeVariant: 'neutral' },
      { name: 'Audit Logs', href: '/audit', icon: ShieldCheck, badge: 'Gov', badgeVariant: 'neutral' },
    ],
  },
  {
    label: 'Configuration',
    items: [
      { name: 'Company & Team', href: '/settings', icon: Settings },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  const getBadgeStyle = (variant?: 'orange' | 'forest' | 'amber' | 'sand' | 'neutral') => {
    switch (variant) {
      case 'orange':
      case 'amber':
        return 'bg-orange-950/70 text-[#FFC247] border-orange-800/50';
      case 'forest':
        return 'bg-emerald-950/70 text-emerald-400 border-emerald-800/50';
      case 'sand':
        return 'bg-[#151515] text-[#A1A1AA] border-[#262626]';
      default:
        return 'bg-[#151515] text-[#737373] border-[#262626]';
    }
  };

  return (
    <aside className="w-64 bg-[#080808] border-r border-[#262626] flex flex-col shrink-0 min-h-screen select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-[#262626]">
        <Logo variant="sidebar" href="/dashboard" />

        {/* Workspace Selector */}
        <div className="mt-3.5">
          <TenantSwitcher />
        </div>
      </div>

      {/* Grouped Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {navGroups.map((group) => (
          <div key={group.label} className="space-y-1">
            <div className="px-3 text-[10px] font-semibold font-mono text-[#737373] uppercase tracking-wider">
              {group.label}
            </div>
            <div className="mt-1 space-y-0.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-editorial ${
                      isActive
                        ? 'bg-[#151515] text-[#F5F5F5] border border-[#262626] shadow-card'
                        : 'text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#101010] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon
                        className={`w-4 h-4 transition-editorial ${
                          isActive ? 'text-[#FF9D00]' : 'text-[#737373]'
                        }`}
                      />
                      <span>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded border font-mono ${getBadgeStyle(
                          item.badgeVariant
                        )}`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer System Status */}
      <div className="p-3.5 border-t border-[#262626] bg-[#050505] text-xs text-[#737373]">
        <div className="flex items-center justify-between font-medium text-[#A1A1AA]">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] text-[#A1A1AA]">Runtime Operational</span>
          </div>
          <span className="text-[10px] font-mono text-[#737373]">v1.0.0</span>
        </div>
        <p className="mt-1 text-[10px] text-[#737373] font-mono">
          Tenant Isolation &amp; Audit Active
        </p>
      </div>
    </aside>
  );
}

