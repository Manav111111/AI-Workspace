import React from 'react';

export type BadgeVariant =
  | 'forest'
  | 'orange'
  | 'amber'
  | 'neutral'
  | 'rose'
  | 'cyan'
  | 'sand'
  | 'emerald'
  | 'outline';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  orange: 'bg-[#FF9D00]/10 text-[#FFC247] border-[#FF9D00]/30',
  amber: 'bg-[#FFC247]/10 text-[#FFC247] border-[#FFC247]/30',
  forest: 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40',
  emerald: 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40',
  neutral: 'bg-[#151515] text-[#A1A1AA] border-[#262626]',
  rose: 'bg-rose-950/40 text-rose-400 border-rose-900/40',
  cyan: 'bg-cyan-950/40 text-cyan-400 border-cyan-900/40',
  sand: 'bg-[#151515] text-[#F5F5F5] border-[#262626]',
  outline: 'bg-transparent text-[#737373] border-[#262626]',
};

const dotStyles: Record<BadgeVariant, string> = {
  orange: 'bg-[#FF9D00]',
  amber: 'bg-[#FFC247]',
  forest: 'bg-emerald-400',
  emerald: 'bg-emerald-400',
  neutral: 'bg-[#737373]',
  rose: 'bg-rose-400',
  cyan: 'bg-cyan-400',
  sand: 'bg-[#A1A1AA]',
  outline: 'bg-[#737373]',
};

export default function Badge({
  children,
  variant = 'neutral',
  size = 'sm',
  dot = false,
  className = '',
}: BadgeProps) {
  const sizeStyle = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-md border tracking-tight ${sizeStyle} ${variantStyles[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotStyles[variant]}`} />}
      {children}
    </span>
  );
}
