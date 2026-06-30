import React, { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`bg-white dark:bg-neutral-900/50 backdrop-blur-xl border border-neutral-200 dark:border-neutral-800/80 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.08)] overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.12)] hover:border-neutral-300 dark:border-neutral-700 ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className = '', ...props }) => (
  <div className={`px-6 sm:px-8 py-6 sm:py-8 border-b border-neutral-200 dark:border-neutral-800/50 ${className}`} {...props} />
);

export const CardTitle: React.FC<HTMLAttributes<HTMLHeadingElement>> = ({ className = '', ...props }) => (
  <h3 className={`text-2xl font-semibold tracking-tight text-neutral-100 ${className}`} {...props} />
);

export const CardDescription: React.FC<HTMLAttributes<HTMLParagraphElement>> = ({ className = '', ...props }) => (
  <p className={`text-base text-neutral-600 dark:text-neutral-500 dark:text-neutral-400 mt-2 ${className}`} {...props} />
);

export const CardContent: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className = '', ...props }) => (
  <div className={`p-6 sm:p-8 ${className}`} {...props} />
);

export const CardFooter: React.FC<HTMLAttributes<HTMLDivElement>> = ({ className = '', ...props }) => (
  <div className={`px-6 sm:px-8 py-5 sm:py-6 border-t border-neutral-200 dark:border-neutral-800/50 bg-white dark:bg-neutral-900/30 flex items-center ${className}`} {...props} />
);
