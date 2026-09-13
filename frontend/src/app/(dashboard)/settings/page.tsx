'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Membership } from '@/types';
import { Settings as SettingsIcon, Building, Users, Shield, CheckCircle } from 'lucide-react';

export default function SettingsPage() {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getCompanies();
        setMemberships(data);
      } catch (err) {
        // Fallback
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings &amp; Workspaces</h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage workspace memberships, team roles, and multi-tenant security policies.
        </p>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-4">
          <Building className="w-4 h-4 text-indigo-400" />
          Authorized Workspaces
        </h2>

        {loading ? (
          <div className="py-4 text-sm text-slate-500">Loading workspaces...</div>
        ) : (
          <div className="space-y-3">
            {memberships.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between p-4 rounded-lg bg-slate-800/40 border border-slate-700/60"
              >
                <div>
                  <h3 className="text-sm font-semibold text-white">{m.company?.name}</h3>
                  <p className="text-xs text-slate-400">Slug: {m.company?.slug}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-medium">
                    Role: {m.role}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-emerald-400" />
          Tenant Isolation Boundary
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Cross-company data access is strictly rejected at the backend database query layer.
          Every request is authenticated via JWT and validated against authorized <code className="text-indigo-300">Membership</code> records.
        </p>
      </div>
    </div>
  );
}
