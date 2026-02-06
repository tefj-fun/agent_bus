import { useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../../utils/utils';

type PdfState =
  | { phase: 'loading' }
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
  const [status, setStatus] = useState<PdfStatus | null>(null);
  const [state, setState] = useState<PdfState>({ phase: 'loading' });
  const objectUrlRef = useRef<string | null>(null);

  const pdfUrl = useMemo(() => {
    if (!artifactId) return '';
    const url = new URL(`/api/artifacts/pdf/${artifactId}`, window.location.origin);
    url.searchParams.set('ts', String(Date.now()));
    return url.toString();
  }, [artifactId]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

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
    const statusUrl = new URL(`/api/artifacts/pdf/${artifactId}/status`, window.location.origin);
    statusUrl.searchParams.set('ts', String(Date.now()));

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

    fetch(statusUrl.toString(), { signal: controller.signal })
      .then(async (res) => {
        if (res.status === 404) {
          // Backward-compatible fallback when status endpoint isn't available
          await fetchPdf();
          return null;
        }
        if (!res.ok) {
          throw new Error(`PDF preview error (${res.status})`);
        }
        return (await res.json()) as PdfStatus;
      })
      .then(async (payload) => {
        if (!payload) return;
        if (!active) return;
        if (payload.available) {
          cleanupObjectUrl();
          setState({ phase: 'ready', src: pdfUrl });
        } else {
          setState({
            phase: 'error',
            detail: payload.detail || emptyMessage,
          });
        }
      })
      .catch((err) => {
        if (!active) return;
        setState({
          phase: 'error',
          detail: err instanceof Error ? err.message : 'Unable to load PDF preview.',
        });
      });

    return () => {
      active = false;
      controller.abort();
      cleanupObjectUrl();
    };
  }, [artifactId, emptyMessage, pdfUrl]);

  return (
    <div className="doc-shell">
      <div className="doc-page doc-page--a4 doc-page--pdf">
        {state.phase === 'loading' && (
          <p className="text-sm text-text-secondary">Loading PDF preview...</p>
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
