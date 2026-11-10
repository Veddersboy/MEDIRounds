import { ChatSession } from "@/lib/types";

/**
 * Standard PDF fonts only support basic Latin characters, so swap common
 * medical symbols for ASCII equivalents and strip Markdown syntax.
 */
function toPlainText(md: string): string {
  return md
    .replace(/≥/g, ">=")
    .replace(/≤/g, "<=")
    .replace(/→/g, "->")
    .replace(/±/g, "+/-")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/```[a-z]*\n?/gi, "")
    .replace(/^\s*\|?[\s:|-]+\|[\s:|-]*$/gm, "") // table separator rows
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(\*|_)(.*?)\1/g, "$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/\|/g, " | ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

type RGB = [number, number, number];

/**
 * Builds a PDF from a chat session and triggers a browser download.
 * Throws on failure so the caller can show an error message.
 */
export async function exportChatAsPdf(session: ChatSession): Promise<void> {
  // Loaded on demand so jsPDF is only downloaded when someone exports
  const { jsPDF } = await import("jspdf");

  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const margin = 56;
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const maxW = pageW - margin * 2;
  let y = margin;

  const write = (
    text: string,
    opts: {
      size?: number;
      style?: "normal" | "bold" | "italic";
      color?: RGB;
      gap?: number;
    } = {}
  ) => {
    const {
      size = 11,
      style = "normal",
      color = [30, 30, 30] as RGB,
      gap = 6,
    } = opts;
    const lineH = size * 1.4;

    doc.setFont("helvetica", style);
    doc.setFontSize(size);
    doc.setTextColor(color[0], color[1], color[2]);

    for (const line of doc.splitTextToSize(text, maxW) as string[]) {
      if (y + lineH > pageH - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y + size);
      y += lineH;
    }

    y += gap;
  };

  // Title
  write(toPlainText(session.title), { size: 18, style: "bold", gap: 4 });
  write(`Exported ${new Date().toLocaleString()}`, {
    size: 9,
    color: [120, 120, 120],
    gap: 16,
  });

  // Messages
  for (const m of session.messages) {
    const speaker = m.role === "user" ? "User" : "Rounds";
    const time = new Date(m.createdAt).toLocaleString();

    write(`${speaker}  ·  ${time}`, {
      size: 10,
      style: "bold",
      color: m.role === "user" ? [60, 60, 60] : [20, 90, 140],
      gap: 2,
    });

    write(toPlainText(m.content), { size: 11, gap: 6 });

    if (m.citations?.length) {
      write("Sources", {
        size: 9,
        style: "bold",
        color: [90, 90, 90],
        gap: 1,
      });

      m.citations.forEach((c, i) => {
        write(
          `${i + 1}. ${toPlainText(c.title)}${c.url ? ` - ${c.url}` : ""}`,
          { size: 9, color: [90, 90, 90], gap: 1 }
        );
      });
    }

    y += 10;

    // Divider between messages
    if (y + 10 > pageH - margin) {
      doc.addPage();
      y = margin;
    }
    doc.setDrawColor(220);
    doc.line(margin, y, pageW - margin, y);
    y += 16;
  }

  // Page numbers + disclaimer on every page
  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i++) {
    doc.setPage(i);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(140, 140, 140);
    doc.text(
      "Research support only - confirm findings against clinical guidelines and professional judgment.",
      margin,
      pageH - 28
    );
    doc.text(`Page ${i} of ${pages}`, pageW - margin, pageH - 28, {
      align: "right",
    });
  }

  doc.save(`rounds-${session.id}.pdf`);
}