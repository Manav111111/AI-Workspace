'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Membership } from '@/types';
import { Building2, ChevronDown, Check } from 'lucide-react';

export default function TenantSwitcher() {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    async function loadCompanies() {
      try {
        const data = await api.getCompanies();
        setMemberships(data);
        const stored = localStorage.getItem('active_company_id');
        if (stored && data.some((m) => m.company?.id === stored)) {
          setActiveCompanyId(stored);
        } else if (data.length > 0 && data[0].company) {
          setActiveCompanyId(data[0].company.id);
          localStorage.setItem('active_company_id', data[0].company.id);
        }
      } catch (err) {
        // Fallback for unauthenticated or empty states
      }
    }
    loadCompanies();
  }, []);

  const handleSelect = (companyId: string) => {
    setActiveCompanyId(companyId);
    localStorage.setItem('active_company_id', companyId);
    setIsOpen(false);
    window.location.reload();
  };

  const activeMembership = memberships.find((m) => m.company?.id === activeCompanyId);
  const activeName = activeMembership?.company?.name || 'Select Workspace';

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition-colors w-full justify-between"
      >
        <div className="flex items-center gap-2 truncate">
          <Building2 className="w-4 h-4 text-indigo-400 shrink-0" />
          <span className="truncate">{activeName}</span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-1 w-56 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-1 z-50">
          <div className="px-3 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Workspaces
          </div>
          {memberships.length === 0 ? (
            <div className="px-3 py-2 text-xs text-slate-400">No workspaces available</div>
          ) : (
            memberships.map((m) => (
              <button
                key={m.id}
                onClick={() => m.company && handleSelect(m.company.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-sm text-left text-slate-300 hover:bg-slate-800 transition-colors"
              >
                <div className="truncate">
                  <div className="font-medium truncate">{m.company?.name}</div>
                  <div className="text-xs text-slate-400">{m.role}</div>
                </div>
                {m.company?.id === activeCompanyId && (
                  <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
