import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Employee Platform | Enterprise Multi-Tenant SaaS',
  description: 'Production-ready platform for company-specific AI employees with multi-tenant data isolation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0b0f19] text-slate-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
