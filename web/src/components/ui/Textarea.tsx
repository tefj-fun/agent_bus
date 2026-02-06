import { forwardRef, type TextareaHTMLAttributes } from 'react';
import { cn } from '../../utils/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  charCount?: {
    current: number;
    min?: number;
    max?: number;
  };
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, hint, error, charCount, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    const isUnderMin = charCount?.min && charCount.current < charCount.min;
    const isOverMax = charCount?.max && charCount.current > charCount.max;

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
        <textarea
          ref={ref}
          id={inputId}
          className={cn(
            'block w-full rounded-lg border bg-bg-primary px-3 py-2 text-sm text-text-primary transition-colors min-h-[120px] resize-y',
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
        <div className="flex justify-between items-center">
          <div>
            {hint && !error && (
              <p className="text-sm text-text-secondary">{hint}</p>
            )}
            {error && (
              <p className="text-sm text-error-600">{error}</p>
            )}
          </div>
          {charCount && (
            <p
              className={cn(
                'text-sm',
                isUnderMin || isOverMax ? 'text-error-600' : 'text-text-secondary'
              )}
            >
              {charCount.current}
              {charCount.min && ` / ${charCount.min} min`}
              {charCount.max && ` / ${charCount.max} max`}
              {charCount.min && charCount.current >= charCount.min && (
                <span className="text-success-600 ml-1">✓</span>
              )}
            </p>
          )}
        </div>
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };
