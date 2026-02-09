import { useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../../utils/utils';

type PdfStatus = { available: boolean; detail?: string };

type PdfState =
  | { phase: 'loading'; detail?: string }
  | { phase: 'ready'; src: string }
  | { phase: 'error'; detail: string };

export function PdfPreview({
  artifactId,
  className,
  emptyMessage = 'PDF preview unavailable.',
}: {
  artifactId?: string;
  className?: string;
  emptyMessage?: string;
}) {
  const [state, setState] = useState<PdfState>({ phase: 'loading' });
  const objectUrlRef = useRef<string | null>(null);

  const makePdfUrl = useMemo(() => {
    return () => {
      if (!artifactId) return '';
      const url = new URL(`/api/artifacts/pdf/${artifactId}`, window.location.origin);
      url.searchParams.set('ts', String(Date.now()));
      return url.toString();
    };
  }, [artifactId]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const MAX_POLLS = 120; // ~6 minutes at 3s interval
    const POLL_MS = 3000;

    const cleanupObjectUrl = () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };

    if (!artifactId) {
      cleanupObjectUrl();
      setState({ phase: 'error', detail: emptyMessage });
      return () => {
        active = false;
        controller.abort();
      };
    }

    setState({ phase: 'loading' });

    const fetchPdf = async () => {
      const pdfEndpoint = new URL(`/api/artifacts/pdf/${artifactId}`, window.location.origin);
      pdfEndpoint.searchParams.set('ts', String(Date.now()));
      const res = await fetch(pdfEndpoint.toString(), { signal: controller.signal });
      if (!res.ok) {
        throw new Error(`PDF preview error (${res.status})`);
      }
      const blob = await res.blob();
      cleanupObjectUrl();
      const objUrl = URL.createObjectURL(blob);
      objectUrlRef.current = objUrl;
      if (active) {
        setState({ phase: 'ready', src: objUrl });
      }
    };

    const pollStatus = async (attempt: number) => {
      const statusUrl = new URL(`/api/artifacts/pdf/${artifactId}/status`, window.location.origin);
      statusUrl.searchParams.set('ts', String(Date.now()));

      try {
        const res = await fetch(statusUrl.toString(), { signal: controller.signal });
        if (res.status === 404) {
          // Backward-compatible fallback when status endpoint isn't available
          await fetchPdf();
          return;
        }
        if (!res.ok) {
          throw new Error(`PDF preview error (${res.status})`);
        }
        const payload = (await res.json()) as PdfStatus;
        if (!active) return;

        if (payload.available) {
          cleanupObjectUrl();
          // Use a fresh cache-buster when switching to the server-rendered PDF.
          setState({ phase: 'ready', src: makePdfUrl() });
          return;
        }

        // Keep polling while backend generates the PDF (status endpoint should be fast).
        const detail = payload.detail || 'PDF not ready yet. Generating...';
        setState({ phase: 'loading', detail });

        if (attempt >= MAX_POLLS) {
          setState({
            phase: 'error',
            detail: `PDF is taking longer than expected. ${detail}`,
          });
          return;
        }
        setTimeout(() => {
          if (!active) return;
          void pollStatus(attempt + 1);
        }, POLL_MS);
      } catch (err) {
        if (!active) return;
        setState({
          phase: 'error',
          detail: err instanceof Error ? err.message : 'Unable to load PDF preview.',
        });
      }
    };

    void pollStatus(0);

    return () => {
      active = false;
      controller.abort();
      cleanupObjectUrl();
    };
  }, [artifactId, emptyMessage, makePdfUrl]);

  return (
    <div className="doc-shell">
      <div className="doc-page doc-page--a4 doc-page--pdf">
        {state.phase === 'loading' && (
          <p className="text-sm text-text-secondary">
            {state.detail || 'Loading PDF preview...'}
          </p>
        )}
        {state.phase === 'error' && (
          <p className="text-sm text-text-secondary">
            {state.detail}
          </p>
        )}
        {state.phase === 'ready' && (
          <iframe
            title="PDF preview"
            src={state.src}
            className={cn('w-full h-[80vh] border-0', className)}
          />
        )}
      </div>
    </div>
  );
}
