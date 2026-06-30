import React, { InputHTMLAttributes } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', ...props }, ref) => {
    return (
      <input
        className={`flex h-11 w-full rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/50 px-4 py-2 text-sm text-neutral-100 transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-neutral-600 dark:text-neutral-500 hover:border-neutral-300 dark:border-neutral-700 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export const Label: React.FC<React.LabelHTMLAttributes<HTMLLabelElement>> = ({ className = '', ...props }) => (
  <label
    className={`block text-xs uppercase tracking-wider font-semibold text-neutral-600 dark:text-neutral-500 dark:text-neutral-400 mb-1.5 ${className}`}
    {...props}
  />
);
