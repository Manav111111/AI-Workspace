import React from 'react';
import Image from 'next/image';
import Link from 'next/link';

export type LogoVariant = 'full' | 'icon' | 'sidebar';

interface LogoProps {
  variant?: LogoVariant;
  className?: string;
  href?: string;
  width?: number;
  height?: number;
  priority?: boolean;
}

export default function Logo({
  variant = 'full',
  className = '',
  href,
  width,
  height,
  priority = false,
}: LogoProps) {
  const renderContent = () => {
    switch (variant) {
      case 'full':
        return (
          <div className={`relative flex items-center ${className}`}>
            <Image
              src="/brand/avtaar-logo.png"
              alt="Avtaar — AI Employees. Real Impact."
              width={width || 170}
              height={height || 56}
              className="h-9 w-auto object-contain"
              priority={priority}
            />
          </div>
        );

      case 'icon':
        return (
          <div className={`relative flex items-center justify-center ${className}`}>
            <Image
              src="/brand/avtaar-icon.png"
              alt="Avtaar"
              width={width || 32}
              height={height || 32}
              className="w-8 h-8 object-contain rounded"
              priority={priority}
            />
          </div>
        );

      case 'sidebar':
        return (
          <div className={`flex items-center gap-2.5 ${className}`}>
            <div className="w-8 h-8 rounded-lg bg-[#101010] border border-[#262626] flex items-center justify-center overflow-hidden shrink-0 shadow-sm">
              <Image
                src="/brand/avtaar-icon.png"
                alt="Avtaar"
                width={26}
                height={26}
                className="w-6 h-6 object-contain"
                priority={priority}
              />
            </div>
            <div className="flex flex-col">
              <span className="font-display font-bold text-base text-[#F5F5F5] tracking-tight leading-none">
                Avtaa<span className="text-[#FF9D00]">r</span>
              </span>
              <span className="text-[9px] font-mono text-[#737373] tracking-wider uppercase mt-0.5 leading-none">
                Control Plane
              </span>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (href) {
    return (
      <Link href={href} className="inline-flex items-center transition-opacity hover:opacity-90">
        {renderContent()}
      </Link>
    );
  }

  return renderContent();
}
