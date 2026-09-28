import React from 'react';
import Button from './Button';

interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  actionIcon?: React.ElementType;
  className?: string;
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
  actionIcon,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`py-12 px-6 text-center border border-dashed border-[#262626] rounded-xl bg-[#0B0B0B]/40 flex flex-col items-center justify-center ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4 shadow-card">
        <Icon className="w-5 h-5 text-[#FF9D00]" />
      </div>
      <h3 className="text-base font-display font-semibold text-[#F5F5F5] tracking-tight">{title}</h3>
      <p className="text-xs sm:text-sm text-[#737373] mt-1.5 max-w-md leading-relaxed font-sans">
        {description}
      </p>
      {actionText && onAction && (
        <div className="mt-5">
          <Button
            variant="primary"
            size="sm"
            onClick={onAction}
            icon={actionIcon}
          >
            {actionText}
          </Button>
        </div>
      )}
    </div>
  );
}

