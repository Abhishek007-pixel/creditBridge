import React, { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-semibold transition-all duration-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-[2px] active:scale-[0.98] min-h-[44px]';
  
  const variants = {
    primary: 'bg-primary-600 text-white hover:bg-primary-500 shadow-md shadow-primary-900/20 hover:shadow-lg hover:shadow-primary-900/30',
    secondary: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-100 hover:bg-neutral-700 border border-neutral-300 dark:border-neutral-700 shadow-sm hover:shadow-md',
    ghost: 'text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:text-white hover:bg-neutral-100 dark:bg-neutral-800/50',
    outline: 'border-2 border-primary-600 text-primary-500 hover:bg-primary-600/10',
    danger: 'bg-red-600/10 text-red-500 hover:bg-red-600/20 border border-red-500/20',
  };

  const sizes = {
    sm: 'text-sm px-4 py-2 min-h-[40px]',
    md: 'text-base px-6 py-3 min-h-[48px]',
    lg: 'text-lg px-8 py-4 min-h-[56px]',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      ) : null}
      {children}
    </button>
  );
};
