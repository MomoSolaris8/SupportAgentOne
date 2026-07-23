import type { ReactNode } from "react";

export function MarkdownText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let currentList: string[] = [];

  function flushList(keyPrefix: string) {
    if (!currentList.length) return;

    blocks.push(
      <ul key={`${keyPrefix}-list-${blocks.length}`}>
        {currentList.map((item, index) => (
          <li key={`${keyPrefix}-item-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    currentList = [];
  }

  text.split(/\n+/).forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList(`line-${index}`);
      return;
    }
    if (trimmed.startsWith("- ")) {
      currentList.push(trimmed.slice(2));
      return;
    }
    flushList(`line-${index}`);
    blocks.push(<p key={`line-${index}`}>{renderInlineMarkdown(trimmed)}</p>);
  });
  flushList("end");

  return <div className="markdownAnswer">{blocks}</div>;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
