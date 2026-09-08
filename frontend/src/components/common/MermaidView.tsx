import { useEffect, useMemo, useRef, useState } from "react";
import mermaid from "mermaid";
import { AlertTriangle } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

let initialised = "";

export function MermaidView({ code, testId = "mermaid-view" }: { code: string; testId?: string }) {
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState("");
  const id = useMemo(() => `mmd-${Math.random().toString(36).slice(2, 10)}`, []);

  useEffect(() => {
    const config = {
      startOnLoad: false,
      securityLevel: "strict" as const,
      theme: theme === "dark" ? ("dark" as const) : ("neutral" as const),
      fontFamily: "JetBrains Mono, monospace",
      themeVariables:
        theme === "dark"
          ? {
              primaryColor: "#0F0F0F",
              primaryTextColor: "#F4F4F5",
              primaryBorderColor: "#00E5FF",
              lineColor: "#A1A1AA",
              secondaryColor: "#141414",
              tertiaryColor: "#0A0A0A",
              background: "#050505",
            }
          : {
              primaryColor: "#FFFFFF",
              primaryTextColor: "#09090B",
              primaryBorderColor: "#0055FF",
              lineColor: "#71717A",
            },
    };
    const signature = `${theme}`;
    if (initialised !== signature) {
      mermaid.initialize(config);
      initialised = signature;
    }
    let cancelled = false;
    (async () => {
      if (!code?.trim()) {
        setSvg("");
        setError(null);
        return;
      }
      try {
        const { svg: rendered } = await mermaid.render(id, code.trim());
        if (!cancelled) {
          setSvg(rendered);
          setError(null);
        }
      } catch (renderError) {
        if (!cancelled) {
          setSvg("");
          setError(renderError instanceof Error ? renderError.message : "Diagram failed to render");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, theme, id]);

  if (error) {
    return (
      <div
        className="flex items-start gap-2 border border-signal-medium/50 bg-signal-medium/5 p-4 text-xs"
        data-testid={`${testId}-error`}
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-signal-medium" />
        <div>
          <p className="font-mono uppercase tracking-wider text-signal-medium">Render failed</p>
          <p className="mt-1 text-muted-foreground">{error}</p>
          <p className="mt-2 text-muted-foreground">Edit the source below and press Save to fix it.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex w-full justify-center overflow-x-auto p-4 [&_svg]:h-auto [&_svg]:max-w-full"
      data-testid={testId}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
