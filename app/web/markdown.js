(function (root) {
  "use strict";

  const CODE_TOKEN_OPEN = "\uE000";
  const CODE_TOKEN_CLOSE = "\uE001";
  const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
  }

  function normalizeMarkdown(value) {
    return String(value ?? "").replace(/\r\n?/g, "\n").replace(/\u0000/g, "");
  }

  function sanitizeUrl(url) {
    const trimmed = String(url ?? "").trim();
    if (!trimmed) {
      return "";
    }

    const compact = trimmed.replace(/[\u0000-\u001F\u007F\s]+/g, "");
    if (!compact) {
      return "";
    }

    if (
      compact.startsWith("#") ||
      compact.startsWith("/") ||
      compact.startsWith("./") ||
      compact.startsWith("../")
    ) {
      return compact;
    }

    try {
      const base =
        root.location && root.location.origin ? root.location.origin : "https://learny.local";
      const parsed = new URL(compact, base);
      return SAFE_PROTOCOLS.has(parsed.protocol) ? compact : "";
    } catch (_error) {
      return "";
    }
  }

  function parseLinkDestination(destination) {
    const raw = String(destination ?? "").trim();
    const withoutWrapping = raw.replace(/^<(.+)>$/, "$1");
    const titled = withoutWrapping.match(/^(\S+)\s+["']([^"']+)["']$/);
    if (titled) {
      return { url: titled[1], title: titled[2] };
    }
    return { url: withoutWrapping, title: "" };
  }

  function stashHtml(stash, html) {
    const token = `${CODE_TOKEN_OPEN}${stash.length}${CODE_TOKEN_CLOSE}`;
    stash.push(html);
    return token;
  }

  function restoreHtml(html, stash) {
    return html.replace(/\uE000(\d+)\uE001/g, (_match, index) => stash[Number(index)] || "");
  }

  function renderInline(markdown, depth = 0) {
    const stash = [];
    let text = normalizeMarkdown(markdown);

    text = text.replace(/(`+)([\s\S]*?[^`])\1/g, (_match, _ticks, code) =>
      stashHtml(stash, `<code>${escapeHtml(code.trim())}</code>`),
    );

    text = text.replace(
      /!\[([^\]]*)\]\(([^)\n]+)\)/g,
      (match, altText, destination) => {
        const { url, title } = parseLinkDestination(destination);
        const safeUrl = sanitizeUrl(url);
        if (!safeUrl) {
          return match;
        }

        const titleAttribute = title ? ` title="${escapeAttribute(title)}"` : "";
        return stashHtml(
          stash,
          `<img src="${escapeAttribute(safeUrl)}" alt="${escapeAttribute(altText)}"${titleAttribute}>`,
        );
      },
    );

    text = text.replace(
      /\[([^\]\n]+)\]\(([^)\n]+)\)/g,
      (match, label, destination) => {
        const { url, title } = parseLinkDestination(destination);
        const safeUrl = sanitizeUrl(url);
        if (!safeUrl) {
          return match;
        }

        const titleAttribute = title ? ` title="${escapeAttribute(title)}"` : "";
        const renderedLabel = depth < 2 ? renderInline(label, depth + 1) : escapeHtml(label);
        return stashHtml(
          stash,
          `<a href="${escapeAttribute(safeUrl)}"${titleAttribute} target="_blank" rel="noopener noreferrer">${renderedLabel}</a>`,
        );
      },
    );

    text = text.replace(/<((?:https?:\/\/|mailto:)[^>\s]+)>/gi, (match, url) => {
      const safeUrl = sanitizeUrl(url);
      if (!safeUrl) {
        return match;
      }
      return stashHtml(
        stash,
        `<a href="${escapeAttribute(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a>`,
      );
    });

    let html = escapeHtml(text);
    html = html.replace(/(\*\*|__)(?=\S)([\s\S]*?\S)\1/g, "<strong>$2</strong>");
    html = html.replace(/~~(?=\S)([\s\S]*?\S)~~/g, "<del>$1</del>");
    html = html.replace(/(^|[^\w*])(\*|_)(?=\S)([^*_]*?\S)\2/g, "$1<em>$3</em>");

    return restoreHtml(html, stash);
  }

  function renderInlineWithBreaks(markdown) {
    return renderInline(markdown).replace(/\n/g, "<br>");
  }

  function isBlank(line) {
    return !line || /^\s*$/.test(line);
  }

  function countIndent(line) {
    return (line.match(/^\s*/) || [""])[0].replace(/\t/g, "    ").length;
  }

  function listMatch(line) {
    const match = String(line ?? "").match(/^(\s*)([-+*]|\d+[.)])\s+(.*)$/);
    if (!match) {
      return null;
    }

    return {
      indent: match[1].replace(/\t/g, "    ").length,
      ordered: /\d/.test(match[2]),
      content: match[3],
    };
  }

  function fenceMatch(line) {
    return String(line ?? "").match(/^\s{0,3}(```|~~~)\s*([A-Za-z0-9_-]*)\s*$/);
  }

  function isHeading(line) {
    return /^ {0,3}#{1,6}\s+\S/.test(line);
  }

  function isHorizontalRule(line) {
    return /^ {0,3}([-*_])(?:\s*\1){2,}\s*$/.test(line);
  }

  function isBlockquote(line) {
    return /^ {0,3}>\s?/.test(line);
  }

  function isIndentedCode(line) {
    return /^( {4}|\t)/.test(line);
  }

  function isTableSeparator(line) {
    const cells = splitTableRow(line);
    return (
      cells.length > 1 &&
      cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
    );
  }

  function isTableStart(lines, index) {
    return (
      index + 1 < lines.length &&
      String(lines[index]).includes("|") &&
      isTableSeparator(lines[index + 1])
    );
  }

  function startsBlock(lines, index) {
    const line = lines[index] || "";
    return (
      isBlank(line) ||
      Boolean(fenceMatch(line)) ||
      isHeading(line) ||
      isHorizontalRule(line) ||
      isBlockquote(line) ||
      Boolean(listMatch(line)) ||
      isIndentedCode(line) ||
      isTableStart(lines, index)
    );
  }

  function trimCodeIndent(line) {
    return line.startsWith("\t") ? line.slice(1) : line.replace(/^ {4}/, "");
  }

  function splitTableRow(line) {
    let row = String(line ?? "").trim();
    if (row.startsWith("|")) {
      row = row.slice(1);
    }
    if (row.endsWith("|")) {
      row = row.slice(0, -1);
    }

    const cells = [];
    let current = "";
    let escaped = false;
    for (const character of row) {
      if (escaped) {
        current += character;
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === "|") {
        cells.push(current.trim());
        current = "";
      } else {
        current += character;
      }
    }
    cells.push(current.trim());
    return cells;
  }

  function tableAlign(separator) {
    const trimmed = separator.trim();
    if (trimmed.startsWith(":") && trimmed.endsWith(":")) {
      return "center";
    }
    if (trimmed.endsWith(":")) {
      return "right";
    }
    if (trimmed.startsWith(":")) {
      return "left";
    }
    return "";
  }

  function renderTable(lines, startIndex) {
    const headers = splitTableRow(lines[startIndex]);
    const separators = splitTableRow(lines[startIndex + 1]);
    const aligns = separators.map(tableAlign);
    let index = startIndex + 2;
    const bodyRows = [];

    while (index < lines.length && String(lines[index]).includes("|") && !isBlank(lines[index])) {
      bodyRows.push(splitTableRow(lines[index]));
      index += 1;
    }

    const alignAttribute = (align) => (align ? ` style="text-align: ${align}"` : "");
    const headerHtml = headers
      .map((cell, cellIndex) => `<th${alignAttribute(aligns[cellIndex])}>${renderInline(cell)}</th>`)
      .join("");
    const bodyHtml = bodyRows
      .map((row) => {
        const cells = headers.map((_header, cellIndex) => row[cellIndex] || "");
        return `<tr>${cells
          .map((cell, cellIndex) => `<td${alignAttribute(aligns[cellIndex])}>${renderInline(cell)}</td>`)
          .join("")}</tr>`;
      })
      .join("");

    return {
      html: `<div class="markdown-table-wrap"><table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`,
      index,
    };
  }

  function renderListItem(contentLines) {
    const content = contentLines.join("\n").trim();
    const task = content.match(/^\[( |x|X)\]\s+([\s\S]*)$/);
    if (task) {
      const checked = task[1].toLowerCase() === "x" ? " checked" : "";
      return `<label class="task-list-item"><input type="checkbox" disabled${checked}><span>${renderInlineWithBreaks(
        task[2],
      )}</span></label>`;
    }

    return renderInlineWithBreaks(content);
  }

  function renderList(lines, startIndex, baseIndent, ordered) {
    let index = startIndex;
    const tag = ordered ? "ol" : "ul";
    let html = `<${tag}>`;

    while (index < lines.length) {
      const current = listMatch(lines[index]);
      if (!current || current.indent < baseIndent || current.ordered !== ordered) {
        break;
      }

      if (current.indent > baseIndent) {
        break;
      }

      const contentLines = [current.content];
      let nestedHtml = "";
      index += 1;

      while (index < lines.length) {
        const next = listMatch(lines[index]);
        if (next) {
          if (next.indent > baseIndent) {
            const nested = renderList(lines, index, next.indent, next.ordered);
            nestedHtml += nested.html;
            index = nested.index;
            continue;
          }
          break;
        }

        if (isBlank(lines[index])) {
          index += 1;
          break;
        }

        if (countIndent(lines[index]) > baseIndent) {
          contentLines.push(lines[index].trim());
          index += 1;
          continue;
        }

        break;
      }

      const isTaskItem = /^\[( |x|X)\]\s+/.test(contentLines.join("\n").trim());
      const taskClass = isTaskItem ? ' class="task-list-entry"' : "";
      html += `<li${taskClass}>${renderListItem(contentLines)}${nestedHtml}</li>`;
    }

    html += `</${tag}>`;
    return { html, index };
  }

  function renderMarkdown(markdown) {
    const source = normalizeMarkdown(markdown);
    const lines = source.split("\n");
    const blocks = [];
    let index = 0;

    while (index < lines.length) {
      const line = lines[index] || "";

      if (isBlank(line)) {
        index += 1;
        continue;
      }

      const fence = fenceMatch(line);
      if (fence) {
        const marker = fence[1];
        const language = fence[2] || "";
        const codeLines = [];
        index += 1;
        while (index < lines.length && !new RegExp(`^\\s{0,3}${marker}`).test(lines[index])) {
          codeLines.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) {
          index += 1;
        }

        const languageClass = language ? ` class="language-${escapeAttribute(language)}"` : "";
        blocks.push(`<pre><code${languageClass}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        continue;
      }

      if (isIndentedCode(line)) {
        const codeLines = [];
        while (index < lines.length && (isIndentedCode(lines[index]) || isBlank(lines[index]))) {
          codeLines.push(isBlank(lines[index]) ? "" : trimCodeIndent(lines[index]));
          index += 1;
        }
        blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n").replace(/\n+$/, ""))}</code></pre>`);
        continue;
      }

      if (isTableStart(lines, index)) {
        const table = renderTable(lines, index);
        blocks.push(table.html);
        index = table.index;
        continue;
      }

      if (isHeading(line)) {
        const heading = line.match(/^ {0,3}(#{1,6})\s+(.+)$/);
        const level = heading[1].length;
        blocks.push(`<h${level}>${renderInline(heading[2].replace(/\s+#+\s*$/, ""))}</h${level}>`);
        index += 1;
        continue;
      }

      if (isHorizontalRule(line)) {
        blocks.push("<hr>");
        index += 1;
        continue;
      }

      if (isBlockquote(line)) {
        const quoteLines = [];
        while (index < lines.length && (isBlockquote(lines[index]) || isBlank(lines[index]))) {
          quoteLines.push(lines[index].replace(/^ {0,3}>\s?/, ""));
          index += 1;
        }
        blocks.push(`<blockquote>${renderMarkdown(quoteLines.join("\n"))}</blockquote>`);
        continue;
      }

      const currentList = listMatch(line);
      if (currentList) {
        const list = renderList(lines, index, currentList.indent, currentList.ordered);
        blocks.push(list.html);
        index = list.index;
        continue;
      }

      const paragraphLines = [line];
      index += 1;
      while (index < lines.length && !startsBlock(lines, index)) {
        paragraphLines.push(lines[index]);
        index += 1;
      }
      blocks.push(`<p>${renderInlineWithBreaks(paragraphLines.join("\n"))}</p>`);
    }

    return blocks.join("\n");
  }

  const api = {
    escapeHtml,
    renderMarkdown,
    sanitizeUrl,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  root.LearnyMarkdown = api;
})(typeof window !== "undefined" ? window : globalThis);
