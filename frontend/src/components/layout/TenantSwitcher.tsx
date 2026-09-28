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
        className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#F5F5F5] bg-[#101010] hover:bg-[#151515] border border-[#262626] hover:border-[#383838] rounded-lg transition-editorial w-full justify-between shadow-card"
      >
        <div className="flex items-center gap-2 truncate">
          <Building2 className="w-3.5 h-3.5 text-[#FF9D00] shrink-0" />
          <span className="truncate font-medium tracking-tight">{activeName}</span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-[#737373] shrink-0" />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-1.5 w-60 bg-[#101010] border border-[#262626] rounded-lg shadow-card py-1.5 z-50">
          <div className="px-3 py-1 text-[10px] font-bold text-[#737373] uppercase tracking-wider font-mono">
            Workspaces
          </div>
          {memberships.length === 0 ? (
            <div className="px-3 py-2 text-xs text-[#737373]">No workspaces found</div>
          ) : (
            memberships.map((m) => (
              <button
                key={m.id}
                onClick={() => m.company && handleSelect(m.company.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-xs text-left text-[#A1A1AA] hover:bg-[#151515] hover:text-[#F5F5F5] transition-editorial"
              >
                <div className="truncate">
                  <div className="font-medium truncate text-[#F5F5F5]">{m.company?.name}</div>
                  <div className="text-[10px] text-[#737373] font-mono">Role: {m.role}</div>
                </div>
                {m.company?.id === activeCompanyId && (
                  <Check className="w-3.5 h-3.5 text-[#FF9D00] shrink-0" />
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

