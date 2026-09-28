import React from 'react';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[#050505] text-[#F5F5F5] font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 bg-[#050505]">
        <Header />
        <main className="flex-1 p-6 sm:p-8 overflow-y-auto bg-[#050505]">{children}</main>
      </div>
    </div>
  );
}

