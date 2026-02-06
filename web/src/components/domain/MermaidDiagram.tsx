import { useEffect, useId, useRef, useState, useCallback, type PointerEvent, type MouseEvent as ReactMouseEvent } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, RefreshCcw, Maximize2, Minimize2, Move } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../utils/utils';

let mermaidInitialized = false;
let lastThemeKey = '';

const baseConfig = {
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
} as const;

const resolveThemeVariables = () => {
  if (typeof window === 'undefined') {
    return {
      primaryColor: '#e5edff',
      primaryTextColor: '#111827',
      primaryBorderColor: '#c7d2fe',
      lineColor: '#6b7280',
      fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    };
  }

  const styles = getComputedStyle(document.documentElement);
  const readVar = (name: string, fallback: string) => {
    const value = styles.getPropertyValue(name).trim();
    if (!value) return fallback;
    const lower = value.toLowerCase();
    if (
      lower.startsWith('var(') ||
      lower.startsWith('oklch') ||
      lower.startsWith('oklab') ||
      lower.startsWith('lab(') ||
      lower.startsWith('color(')
    ) {
      return fallback;
    }
    return value;
  };

  return {
    primaryColor: readVar('--color-primary-100', '#e5edff'),
    primaryTextColor: readVar('--color-text-primary', '#111827'),
    primaryBorderColor: readVar('--color-primary-300', '#c7d2fe'),
    lineColor: readVar('--color-text-muted', '#6b7280'),
    fontFamily: readVar('--font-sans', 'Inter, ui-sans-serif, system-ui, sans-serif'),
  };
};

const initializeMermaid = () => {
  const themeVariables = resolveThemeVariables();
  const themeKey = JSON.stringify(themeVariables);
  if (!mermaidInitialized || themeKey !== lastThemeKey) {
    mermaid.initialize({
      ...baseConfig,
      themeVariables,
    });
    mermaidInitialized = true;
    lastThemeKey = themeKey;
  }
};

type MermaidDiagramProps = {
  chart: string;
  interactive?: boolean;
  showToolbar?: boolean;
  onToggleFullscreen?: () => void;
  isFullscreen?: boolean;
  containerClassName?: string;
  onNodeClick?: (nodeId: string) => void;
  fitKey?: string;
};

export function MermaidDiagram({
  chart,
  interactive = true,
  showToolbar = true,
  onToggleFullscreen,
  isFullscreen = false,
  containerClassName,
  onNodeClick,
  fitKey,
}: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const renderId = useId().replace(/:/g, '');
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [isFitReady, setIsFitReady] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const panOriginRef = useRef({ x: 0, y: 0, startX: 0, startY: 0 });
  const isPanningRef = useRef(false);
  const hasMovedRef = useRef(false);
  const lastFitKeyRef = useRef<string>('');
  const pendingAnchorRef = useRef<{ id: string; x: number; y: number } | null>(null);

  const clampScale = useCallback((value: number) => Math.min(6, Math.max(0.2, value)), []);

  const fitToView = useCallback(() => {
    const container = containerRef.current;
    const content = contentRef.current;
    if (!container || !content) return;

    const svgEl = content.querySelector('svg');
    if (!svgEl) return;

    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const svgRect = svgEl.getBoundingClientRect();
    if (!svgRect.width || !svgRect.height) return;

    const parseSize = (value: string | null) => {
      if (!value) return 0;
      if (value.endsWith('%')) return 0;
      const parsed = Number.parseFloat(value);
      return Number.isFinite(parsed) ? parsed : 0;
    };

    let viewBoxX = 0;
    let viewBoxY = 0;
    let viewBoxWidth = 0;
    let viewBoxHeight = 0;
    let contentBox:
      | { x: number; y: number; width: number; height: number }
      | undefined;

    const viewBox = svgEl.viewBox?.baseVal;
    if (viewBox && viewBox.width && viewBox.height) {
      viewBoxX = viewBox.x;
      viewBoxY = viewBox.y;
      viewBoxWidth = viewBox.width;
      viewBoxHeight = viewBox.height;
    } else {
      viewBoxWidth = parseSize(svgEl.getAttribute('width'));
      viewBoxHeight = parseSize(svgEl.getAttribute('height'));
    }

    if (!viewBoxWidth || !viewBoxHeight) {
      viewBoxWidth = svgRect.width;
      viewBoxHeight = svgRect.height;
    }

    try {
      const bbox = svgEl.getBBox();
      if (bbox.width && bbox.height) {
        contentBox = {
          x: bbox.x,
          y: bbox.y,
          width: bbox.width,
          height: bbox.height,
        };
      }
    } catch {
      contentBox = undefined;
    }

    const unitsToPxX = viewBoxWidth ? svgRect.width / viewBoxWidth : 1;
    const unitsToPxY = viewBoxHeight ? svgRect.height / viewBoxHeight : 1;

    const fitBox = contentBox ?? {
      x: viewBoxX,
      y: viewBoxY,
      width: viewBoxWidth,
      height: viewBoxHeight,
    };

    const contentX = fitBox.x * unitsToPxX;
    const contentY = fitBox.y * unitsToPxY;
    const contentWidth = fitBox.width * unitsToPxX;
    const contentHeight = fitBox.height * unitsToPxY;
    if (!contentWidth || !contentHeight) return;

    const padding = Math.min(32, rect.width * 0.08, rect.height * 0.08);
    const scale = clampScale(
      Math.min(
        (rect.width - padding * 2) / contentWidth,
        (rect.height - padding * 2) / contentHeight
      )
    );

    const x = (rect.width - contentWidth * scale) / 2 - contentX * scale;
    const y = (rect.height - contentHeight * scale) / 2 - contentY * scale;
    setTransform({ x, y, scale });
    setIsFitReady(true);
  }, [clampScale]);

  const resetView = useCallback(() => {
    fitToView();
  }, [fitToView]);

  useEffect(() => {
    let active = true;
    initializeMermaid();
    if (!chart || !chart.trim()) {
      setSvg('');
      setError(null);
      setIsFitReady(false);
      return () => {
        active = false;
      };
    }

    mermaid
      .render(`mermaid-${renderId}`, chart)
      .then(({ svg }) => {
        if (!active) return;
        setSvg(svg);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err?.message || 'Failed to render diagram');
      });

    return () => {
      active = false;
    };
  }, [chart, renderId]);

  const resolveNodeIdFromTarget = useCallback((target: EventTarget | null) => {
    if (!target || !(target instanceof Element)) return null;
    const node = target.closest('g.node');
    if (!node) return null;
    const title = node.querySelector('title')?.textContent?.trim();
    const dataId = node.getAttribute('data-id') || node.getAttribute('data-node');
    return dataId || title || node.getAttribute('id');
  }, []);

  const resolveNodeElementFromId = useCallback((rawId: string) => {
    const root = contentRef.current;
    if (!root) return null;
    const nodes = root.querySelectorAll<SVGGElement>('g.node');
    for (const node of nodes) {
      const title = node.querySelector('title')?.textContent?.trim();
      const dataId = node.getAttribute('data-id') || node.getAttribute('data-node');
      const candidate = dataId || title || node.getAttribute('id');
      if (candidate === rawId) return node;
    }
    return null;
  }, []);

  const captureAnchorPosition = useCallback((rawId: string, target: EventTarget | null) => {
    const container = containerRef.current;
    if (!container) return;
    let nodeEl = target instanceof Element ? target.closest('g.node') : null;
    if (!nodeEl) {
      nodeEl = resolveNodeElementFromId(rawId);
    }
    if (!nodeEl) return;
    const nodeRect = nodeEl.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    if (!nodeRect.width || !nodeRect.height) return;
    pendingAnchorRef.current = {
      id: rawId,
      x: nodeRect.left + nodeRect.width / 2 - containerRect.left,
      y: nodeRect.top + nodeRect.height / 2 - containerRect.top,
    };
  }, [resolveNodeElementFromId]);

  const applyAnchorAdjustment = useCallback(() => {
    const pending = pendingAnchorRef.current;
    if (!pending) return;
    const container = containerRef.current;
    if (!container) return;
    const nodeEl = resolveNodeElementFromId(pending.id);
    if (!nodeEl) {
      pendingAnchorRef.current = null;
      return;
    }
    const nodeRect = nodeEl.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    if (!nodeRect.width || !nodeRect.height) {
      pendingAnchorRef.current = null;
      return;
    }
    const nextX = nodeRect.left + nodeRect.width / 2 - containerRect.left;
    const nextY = nodeRect.top + nodeRect.height / 2 - containerRect.top;
    const dx = pending.x - nextX;
    const dy = pending.y - nextY;
    pendingAnchorRef.current = null;
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
    setTransform((prev) => ({
      ...prev,
      x: prev.x + dx,
      y: prev.y + dy,
    }));
  }, [resolveNodeElementFromId]);

  useEffect(() => {
    if (!svg) return;
    const nextFitKey = fitKey ?? chart;
    const shouldFit = !lastFitKeyRef.current || lastFitKeyRef.current !== nextFitKey;
    if (!shouldFit) {
      setIsFitReady(true);
      const handle = requestAnimationFrame(() => {
        applyAnchorAdjustment();
      });
      return () => cancelAnimationFrame(handle);
    }

    let cancelled = false;
    lastFitKeyRef.current = nextFitKey;

    const attemptFit = () => {
      if (cancelled) return;
      fitToView();
    };

    const handle = requestAnimationFrame(attemptFit);

    const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
    if (fonts?.ready) {
      fonts.ready.then(() => {
        if (!cancelled) fitToView();
      });
    }

    return () => {
      cancelled = true;
      cancelAnimationFrame(handle);
    };
  }, [applyAnchorAdjustment, chart, fitKey, fitToView, svg]);

  const handleContainerClick = useCallback((event: ReactMouseEvent<HTMLDivElement>) => {
    if (!interactive || !onNodeClick) return;
    if (hasMovedRef.current) {
      hasMovedRef.current = false;
      return;
    }
    const nodeId = resolveNodeIdFromTarget(event.target);
    if (!nodeId) return;
    captureAnchorPosition(nodeId, event.target);
    onNodeClick(nodeId);
  }, [captureAnchorPosition, interactive, onNodeClick, resolveNodeIdFromTarget]);

  const zoomTo = useCallback(
    (nextScale: number, clientX?: number, clientY?: number) => {
      setTransform((prev) => {
        const clamped = clampScale(nextScale);
        if (!containerRef.current || clientX === undefined || clientY === undefined) {
          return { ...prev, scale: clamped };
        }

        const rect = containerRef.current.getBoundingClientRect();
        const cx = clientX - rect.left;
        const cy = clientY - rect.top;
        const ratio = clamped / prev.scale;
        const nextX = cx - (cx - prev.x) * ratio;
        const nextY = cy - (cy - prev.y) * ratio;
        return { x: nextX, y: nextY, scale: clamped };
      });
    },
    [clampScale]
  );

  const handleWheel = useCallback(
    (event: WheelEvent) => {
      if (!interactive) return;
      event.preventDefault();
      const direction = event.deltaY < 0 ? 1.12 : 0.9;
      zoomTo(transform.scale * direction, event.clientX, event.clientY);
    },
    [interactive, transform.scale, zoomTo]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    if (!interactive) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      container.removeEventListener('wheel', handleWheel);
    };
  }, [handleWheel, interactive]);

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!interactive || event.button !== 0) return;
      if (resolveNodeIdFromTarget(event.target)) return;
      setIsPanning(true);
      isPanningRef.current = true;
      hasMovedRef.current = false;
      panOriginRef.current = {
        x: event.clientX,
        y: event.clientY,
        startX: transform.x,
        startY: transform.y,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [interactive, transform.x, transform.y]
  );

  const handlePointerMove = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!interactive || !isPanning) return;
      const dx = event.clientX - panOriginRef.current.x;
      const dy = event.clientY - panOriginRef.current.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
        hasMovedRef.current = true;
      }
      setTransform((prev) => ({
        ...prev,
        x: panOriginRef.current.startX + dx,
        y: panOriginRef.current.startY + dy,
      }));
    },
    [interactive, isPanning]
  );

  const handlePointerUp = useCallback((event: PointerEvent<HTMLDivElement>) => {
    if (!interactive) return;
    setIsPanning(false);
    isPanningRef.current = false;
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // Ignore release errors when pointer was not captured
    }
  }, [interactive]);

  if (error) {
    return (
      <div className="text-sm text-error-600 bg-error-50 border border-error-100 rounded-lg p-3">
        {error}
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="text-sm text-text-secondary border border-dashed border-border rounded-lg p-6 text-center">
        No diagram available yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {showToolbar && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <Move className="w-4 h-4" />
            {onNodeClick ? 'Drag to pan, scroll to zoom, click to collapse' : 'Drag to pan, scroll to zoom'}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              icon={<ZoomOut className="w-4 h-4" />}
              onClick={() => zoomTo(transform.scale * 0.9)}
            >
              Zoom Out
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={<ZoomIn className="w-4 h-4" />}
              onClick={() => zoomTo(transform.scale * 1.12)}
            >
              Zoom In
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCcw className="w-4 h-4" />}
              onClick={resetView}
            >
              Reset
            </Button>
            {onToggleFullscreen && (
              <Button
                variant="outline"
                size="sm"
                icon={isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                onClick={onToggleFullscreen}
              >
                {isFullscreen ? 'Exit Full Screen' : 'Full Screen'}
              </Button>
            )}
          </div>
        </div>
      )}
      <div
        ref={containerRef}
        className={cn(
          'relative w-full overflow-hidden rounded-lg border border-border bg-bg-primary',
          interactive && 'touch-none select-none',
          interactive ? (isPanning ? 'cursor-grabbing' : 'cursor-grab') : 'cursor-default',
          containerClassName
        )}
        style={!containerClassName ? { minHeight: '360px' } : undefined}
        onClick={handleContainerClick}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        <div
          ref={contentRef}
          className="absolute inset-0"
          style={{
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            transformOrigin: '0 0',
            opacity: isFitReady ? 1 : 0,
            transition: 'opacity 120ms ease',
          }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>
    </div>
  );
}
