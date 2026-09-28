import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ElementType;
  badge?: string | number;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({
  tabs,
  activeTab,
  onChange,
  className = '',
}: TabsProps) {
  return (
    <div
      className={`flex items-center gap-1 p-1 bg-[#0B0B0B] border border-[#262626] rounded-lg ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-editorial ${
              isActive
                ? 'bg-[#151515] text-[#F5F5F5] shadow-card border border-[#262626]'
                : 'text-[#737373] hover:text-[#F5F5F5] hover:bg-[#101010]'
            }`}
          >
            {Icon && <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#FF9D00]' : 'text-[#737373]'}`} />}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  isActive
                    ? 'bg-orange-950/80 text-[#FFC247] border border-orange-800/60'
                    : 'bg-[#151515] text-[#737373]'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

