import type { ReactNode } from 'react';
import { Header } from './Header';

interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
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
  backLink?: { href: string; label: string };
}

export function PageHeader({ title, description, actions, backLink }: PageHeaderProps) {
  return (
    <div className="mb-6">
      {backLink && (
        <a
          href={backLink.href}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
        >
          ← {backLink.label}
        </a>
      )}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {description && (
            <div className="text-gray-500 mt-1">{description}</div>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
