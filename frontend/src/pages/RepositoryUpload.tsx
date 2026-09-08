import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { FileArchive, Github, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { Repository } from "@/lib/types";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function RepositoryUpload() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["repositories"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const uploadZip = useMutation({
    mutationFn: async () => {
      const form = new FormData();
      form.append("file", file as File);
      form.append("description", description);
      const { data } = await api.post<Repository>("/repositories/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (repo) => {
      toast.success(`Analysed ${repo.name}`);
      invalidate();
      navigate(`/repositories/${repo.id}`);
    },
    onError: (mutationError) => setError(apiError(mutationError, "Upload failed")),
  });

  const importGithub = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<Repository>("/repositories/github", {
        url: url.trim(),
        branch: branch.trim() || null,
        name: name.trim() || null,
        description,
      });
      return data;
    },
    onSuccess: (repo) => {
      toast.success(`Cloned ${repo.name}`);
      invalidate();
      navigate(`/repositories/${repo.id}`);
    },
    onError: (mutationError) => setError(apiError(mutationError, "Clone failed")),
  });

  const onDrop = useCallback((accepted: File[]) => {
    setError("");
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/zip": [".zip"], "application/x-zip-compressed": [".zip"] },
    maxFiles: 1,
    multiple: false,
  });

  const busy = uploadZip.isPending || importGithub.isPending;

  return (
    <div className="space-y-8" data-testid="upload-page">
      <header className="border-b border-border pb-6">
        <p className="label-mono">Ingestion</p>
        <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter">Add repository</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Upload a ZIP archive or clone a public Git repository. The project is extracted, language and
          framework detected, metrics computed and the codebase embedded into ChromaDB for RAG chat.
        </p>
      </header>

      {error && (
        <p className="border border-signal-critical/60 bg-signal-critical/10 px-4 py-3 text-sm text-signal-critical" data-testid="upload-error">
          {error}
        </p>
      )}

      {busy && (
        <div className="panel flex items-center gap-3 p-4" data-testid="upload-progress">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <p className="font-mono text-xs uppercase tracking-wider">
            {uploadZip.isPending ? "Extracting and analysing archive" : "Cloning and analysing repository"} — this can take a minute
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-6" data-testid="zip-upload-section">
          <div className="mb-5 flex items-center gap-2">
            <FileArchive className="h-4 w-4 text-primary" />
            <h2 className="font-mono text-lg tracking-tight">ZIP archive</h2>
          </div>
          <div
            {...getRootProps()}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 border border-dashed p-10 text-center transition-colors",
              isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/60"
            )}
            data-testid="zip-dropzone"
          >
            <input {...getInputProps()} data-testid="zip-file-input" />
            <UploadCloud className="h-8 w-8 text-muted-foreground" />
            <p className="font-mono text-xs uppercase tracking-wider">
              {isDragActive ? "Drop the archive" : "Drag a .zip here or click to browse"}
            </p>
            <p className="text-xs text-muted-foreground">Max 100 MB · Python, Java, C++, JS, TS, Go and more</p>
          </div>

          {file && (
            <div className="mt-4 flex items-center justify-between border border-border px-4 py-3" data-testid="selected-file">
              <div className="min-w-0">
                <p className="truncate font-mono text-xs">{file.name}</p>
                <p className="label-mono mt-0.5">{formatBytes(file.size)}</p>
              </div>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground hover:text-signal-critical"
                data-testid="clear-file-button"
              >
                Remove
              </button>
            </div>
          )}

          <button
            type="button"
            disabled={!file || busy}
            onClick={() => {
              setError("");
              uploadZip.mutate();
            }}
            className="mt-5 flex h-11 w-full items-center justify-center gap-2 border border-primary bg-primary font-mono text-[11px] uppercase tracking-[0.2em] text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-50"
            data-testid="upload-zip-button"
          >
            {uploadZip.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
            Upload and analyse
          </button>
        </section>

        <section className="panel p-6" data-testid="github-import-section">
          <div className="mb-5 flex items-center gap-2">
            <Github className="h-4 w-4 text-primary" />
            <h2 className="font-mono text-lg tracking-tight">Git repository URL</h2>
          </div>
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="repo_url" className="label-mono">
                Repository URL
              </label>
              <input
                id="repo_url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://github.com/owner/project"
                className="h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="github-url-input"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="repo_branch" className="label-mono">
                  Branch (optional)
                </label>
                <input
                  id="repo_branch"
                  value={branch}
                  onChange={(event) => setBranch(event.target.value)}
                  placeholder="main"
                  className="h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                  data-testid="github-branch-input"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="repo_name" className="label-mono">
                  Display name (optional)
                </label>
                <input
                  id="repo_name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                  data-testid="github-name-input"
                />
              </div>
            </div>
            <button
              type="button"
              disabled={!url.trim() || busy}
              onClick={() => {
                setError("");
                importGithub.mutate();
              }}
              className="flex h-11 w-full items-center justify-center gap-2 border border-primary bg-primary font-mono text-[11px] uppercase tracking-[0.2em] text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-50"
              data-testid="import-github-button"
            >
              {importGithub.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Github className="h-4 w-4" />}
              Clone and analyse
            </button>
            <p className="text-xs text-muted-foreground">
              Public repositories only. A shallow clone (depth 1) is used and the <code className="font-mono">.git</code>{" "}
              directory is discarded after cloning.
            </p>
          </div>
        </section>
      </div>

      <section className="panel p-6" data-testid="shared-description-section">
        <label htmlFor="repo_description" className="label-mono">
          Description (applies to either method)
        </label>
        <textarea
          id="repo_description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          placeholder="Final year project submission — task management microservice"
          className="mt-2 w-full border border-border bg-background p-3 font-sans text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
          data-testid="repo-description-input"
        />
      </section>
    </div>
  );
}
