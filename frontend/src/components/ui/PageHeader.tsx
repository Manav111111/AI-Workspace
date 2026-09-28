import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export default function PageHeader({
  title,
  description,
  badge,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#262626]">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl sm:text-2xl font-display font-bold text-[#F5F5F5] tracking-tight">{title}</h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs sm:text-sm text-[#A1A1AA] mt-1 leading-relaxed max-w-3xl font-sans">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
    </div>
  );
}

