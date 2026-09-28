import React from 'react';
import { Loader2 } from 'lucide-react';

export type ButtonVariant =
  | 'forest'
  | 'primary'
  | 'orange'
  | 'secondary'
  | 'outline'
  | 'ghost'
  | 'danger'
  | 'amber';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ElementType;
  iconRight?: React.ElementType;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-[#FF9D00] hover:bg-[#FF6A00] text-black font-semibold shadow-sm active:bg-[#EA580C] transition-colors',
  orange:
    'bg-[#FF9D00] hover:bg-[#FF6A00] text-black font-semibold shadow-sm active:bg-[#EA580C] transition-colors',
  forest:
    'bg-[#FF9D00] hover:bg-[#FF6A00] text-black font-semibold shadow-sm active:bg-[#EA580C] transition-colors',
  secondary:
    'bg-[#151515] hover:bg-[#1E1E1E] text-[#F5F5F5] font-medium border border-[#262626] hover:border-[#333333] active:bg-[#101010] transition-colors',
  outline:
    'bg-transparent hover:bg-[#151515] text-[#A1A1AA] hover:text-[#F5F5F5] font-medium border border-[#262626] hover:border-[#333333] transition-colors',
  ghost:
    'bg-transparent hover:bg-[#151515] text-[#A1A1AA] hover:text-[#F5F5F5] font-medium transition-colors',
  danger:
    'bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-900/60 font-medium active:bg-rose-950 transition-colors',
  amber:
    'bg-[#FFC247] hover:bg-[#FF9D00] text-black font-semibold shadow-sm transition-colors',
};

const sizeStyles = {
  sm: 'text-xs px-2.5 py-1.5 rounded-md gap-1.5',
  md: 'text-xs sm:text-sm px-3.5 py-2 rounded-lg gap-2',
  lg: 'text-sm sm:text-base px-5 py-2.5 rounded-lg gap-2.5',
};

export default function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  iconRight: IconRight,
  children,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-sans transition-colors focus:outline-none focus:ring-2 focus:ring-[#FF9D00]/40 disabled:opacity-50 disabled:cursor-not-allowed ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" />
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" />
      ) : null}
      <span>{children}</span>
      {!loading && IconRight && <IconRight className="w-4 h-4 shrink-0" />}
    </button>
  );
}
