import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownView({ content, testId = "markdown-view" }: { content: string; testId?: string }) {
  return (
    <div className="markdown-body" data-testid={testId}>
      <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
    </div>
  );
}
