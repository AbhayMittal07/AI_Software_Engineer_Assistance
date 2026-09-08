import { useState } from "react";
import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";
import type { TreeNode } from "@/lib/types";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

function Node({
  node,
  depth,
  onSelect,
  selected,
}: {
  node: TreeNode;
  depth: number;
  onSelect?: (path: string) => void;
  selected?: string;
}) {
  const [open, setOpen] = useState(depth < 1);
  if (node.type === "info") {
    return <p className="pl-4 font-mono text-[11px] text-muted-foreground">{node.name}</p>;
  }
  if (node.type === "file") {
    const isSelected = selected === node.path;
    return (
      <button
        type="button"
        onClick={() => node.path && onSelect?.(node.path)}
        style={{ paddingLeft: depth * 14 + 8 }}
        className={cn(
          "flex w-full items-center gap-2 py-1 pr-2 text-left font-mono text-[11px] transition-colors hover:bg-muted/60",
          isSelected ? "bg-primary/10 text-primary" : "text-muted-foreground"
        )}
        data-testid={`file-node-${node.path}`}
      >
        <File className="h-3 w-3 shrink-0" />
        <span className="truncate">{node.name}</span>
        {node.size ? <span className="ml-auto shrink-0 text-[10px] opacity-60">{formatBytes(node.size)}</span> : null}
      </button>
    );
  }
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        style={{ paddingLeft: depth * 14 + 8 }}
        className="flex w-full items-center gap-2 py-1 pr-2 text-left font-mono text-[11px] text-foreground transition-colors hover:bg-muted/60"
        data-testid={`dir-node-${node.name}`}
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Folder className="h-3 w-3 text-primary" />
        <span className="truncate">{node.name}</span>
      </button>
      {open && (
        <div>
          {(node.children || []).map((child, index) => (
            <Node
              key={`${child.name}-${index}`}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
              selected={selected}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({
  tree,
  onSelect,
  selected,
}: {
  tree?: TreeNode | null;
  onSelect?: (path: string) => void;
  selected?: string;
}) {
  if (!tree || !tree.name) {
    return <p className="p-4 font-mono text-xs text-muted-foreground">No file structure available.</p>;
  }
  return (
    <div className="max-h-[520px] overflow-y-auto py-2" data-testid="file-tree">
      <Node node={tree} depth={0} onSelect={onSelect} selected={selected} />
    </div>
  );
}
