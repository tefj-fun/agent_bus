import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Header } from './Header';

interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-bg-secondary">
      <Header />
      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
}

interface PageHeaderProps {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  backLink?: { href: string; label: string; state?: unknown };
}

export function PageHeader({ title, description, actions, backLink }: PageHeaderProps) {
  return (
    <div className="mb-6">
      {backLink && (
        <Link
          to={backLink.href}
          state={backLink.state}
          className="inline-flex items-center text-sm text-text-secondary hover:text-text-primary mb-2"
        >
          ← {backLink.label}
        </Link>
      )}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
          {description && (
            <div className="text-text-secondary mt-1">{description}</div>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
