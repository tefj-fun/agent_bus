import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '../../utils/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, hint, error, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-text-secondary"
          >
            {label}
            {props.required && <span className="text-error-500 ml-1">*</span>}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'block w-full rounded-lg border bg-bg-primary px-3 py-2 text-sm text-text-primary transition-colors',
            'placeholder:text-text-muted',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            error
              ? 'border-error-200 focus:border-error-500 focus:ring-error-500/20'
              : 'border-border focus:border-primary-500 focus:ring-primary-500/20',
            'disabled:bg-bg-secondary disabled:text-text-muted disabled:cursor-not-allowed',
            className
          )}
          {...props}
        />
        {hint && !error && (
          <p className="text-sm text-text-secondary">{hint}</p>
        )}
        {error && (
          <p className="text-sm text-error-600">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
