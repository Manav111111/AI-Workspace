'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Membership } from '@/types';
import { Building, Shield, ShieldCheck, Lock, Server } from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';

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
    <div className="max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Settings & Workspaces"
        description="Manage workspace memberships, team roles, and multi-tenant security policies."
        badge={<Badge variant="orange">Security & Control Plane</Badge>}
      />

      {/* Authorized Workspaces */}
      <Card>
        <CardHeader>
          <CardTitle subtitle="Workspaces where your account has verified access">
            <div className="flex items-center gap-2">
              <Building className="w-4 h-4 text-[#FF9D00]" />
              <span>Authorized Workspaces</span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-4 text-xs text-[#737373] font-mono">Loading workspaces...</div>
          ) : memberships.length === 0 ? (
            <div className="text-xs text-[#737373]">No workspaces found</div>
          ) : (
            <div className="space-y-3">
              {memberships.map((m) => (
                <div
                  key={m.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg bg-[#0B0B0B] border border-[#262626] hover:border-[#333333] transition-colors gap-3"
                >
                  <div>
                    <h3 className="text-sm font-semibold text-[#F5F5F5] font-display">{m.company?.name}</h3>
                    <p className="text-xs text-[#737373] font-mono mt-0.5">Workspace Slug: {m.company?.slug}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="orange">Role: {m.role}</Badge>
                    <Badge variant="neutral">ID: {m.company?.id.slice(0, 8)}...</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Security & Tenant Isolation Boundary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Card>
          <CardHeader>
            <CardTitle subtitle="Multi-tenant zero-trust guarantees">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#FF9D00]" />
                <span>Tenant Isolation Boundary</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[#A1A1AA] space-y-3 leading-relaxed">
            <p>
              Cross-company data access is strictly rejected at the backend database query layer.
              Every request is authenticated via JWT and validated against authorized <code className="text-[#FF9D00] font-mono bg-[#151515] px-1 py-0.5 rounded border border-[#262626]">Membership</code> records.
            </p>
            <div className="flex items-center gap-2 text-[#FF9D00] font-mono text-[11px] bg-[#151515] p-2.5 rounded-lg border border-[#262626]">
              <Lock className="w-4 h-4 shrink-0 text-[#FF9D00]" />
              <span>tenant_id strictly checked in Qdrant & PostgreSQL</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle subtitle="Production infrastructure specifications">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-[#FFC247]" />
                <span>Runtime Infrastructure</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[#A1A1AA] space-y-3 leading-relaxed">
            <p>
              Avtaar services run on FastAPI with asynchronous job queues, Redis-backed sliding-window distributed rate limiting, and OpenTelemetry instrumentation.
            </p>
            <div className="flex items-center gap-2 text-[#FFC247] font-mono text-[11px] bg-[#151515] p-2.5 rounded-lg border border-[#262626]">
              <Shield className="w-4 h-4 shrink-0 text-[#FFC247]" />
              <span>Automatic PII Redaction for Traces & Audits</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
