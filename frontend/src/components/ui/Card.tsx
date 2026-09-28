import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({
  children,
  className = '',
  hover = false,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-[#101010] border border-[#262626] rounded-xl shadow-card transition-editorial ${
        hover
          ? 'hover:border-[#383838] hover:bg-[#131313] cursor-pointer'
          : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`px-5 py-4 border-b border-[#262626] flex items-center justify-between ${className}`}
    >
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className = '',
  subtitle,
}: {
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
}) {
  return (
    <div>
      <h3 className={`text-sm sm:text-base font-display font-semibold text-[#F5F5F5] tracking-tight ${className}`}>
        {children}
      </h3>
      {subtitle && <p className="text-xs text-[#737373] mt-0.5">{subtitle}</p>}
    </div>
  );
}

export function CardContent({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function CardFooter({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`px-5 py-3 border-t border-[#262626] bg-[#0B0B0B]/80 rounded-b-xl flex items-center justify-between text-xs text-[#737373] ${className}`}
    >
      {children}
    </div>
  );
}

