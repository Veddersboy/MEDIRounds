"use client";

import React, { useState } from "react";
import { Minus, Plus, X } from "lucide-react";

const PMCID_BLOB_RE = /PMC\d+/gi;

export function normalizePmcid(raw: string): string {
  const trimmed = raw.trim().toUpperCase();
  if (!trimmed) throw new Error("Empty PMCID");
  const id = trimmed.startsWith("PMC") ? trimmed : `PMC${trimmed}`;
  if (!/^\d+$/.test(id.slice(3))) {
    throw new Error(`'${raw}' doesn't look like a PMCID`);
  }
  return id;
}

export function extractAllPmcids(text: string): string[] {
  const matches = text.match(PMCID_BLOB_RE);
  if (matches && matches.length > 0) {
    return Array.from(new Set(matches.map((m) => normalizePmcid(m))));
  }

  const tokens = text.replace(/,/g, " ").split(/\s+/).filter(Boolean);
  const ids: string[] = [];
  for (const token of tokens) {
    try {
      ids.push(normalizePmcid(token));
    } catch {
      // Ignore tokens that aren't PMCIDs
    }
  }
  return Array.from(new Set(ids));
}

interface PubMedModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface FetchResult {
  output_dir: string;
  total: number;
  saved: Array<{ id: string; path: string; title?: string; data?: unknown }>;
  skipped: Array<{ id: string; path: string }>;
  errors: Array<{ id: string; error: string }>;
}

export function PubMedModal({ isOpen, onClose }: PubMedModalProps) {
  const [rows, setRows] = useState<string[]>([""]);
  const [outputDir, setOutputDir] = useState("output/pubmed");
  const [dirHandle, setDirHandle] = useState<FileSystemDirectoryHandle | null>(null);
  const [isPasteModalOpen, setIsPasteModalOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");

  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [progressPercent, setProgressPercent] = useState<number | null>(null);
  const [result, setResult] = useState<FetchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddRow = () => {
    setRows((prev) => [...prev, ""]);
  };

  const handleRemoveRow = (index: number) => {
    if (rows.length <= 1) return;
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRowChange = (index: number, val: string) => {
    setRows((prev) => {
      const copy = [...prev];
      copy[index] = val;
      return copy;
    });
  };

  const handleBrowseDirectory = async () => {
    if (typeof window !== "undefined" && "showDirectoryPicker" in window) {
      try {
        // @ts-expect-error File System Access API
        const handle = (await window.showDirectoryPicker()) as FileSystemDirectoryHandle;
        setDirHandle(handle);
        setOutputDir(handle.name);
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          console.error("Directory picker error:", err);
        }
      }
    } else {
      const custom = prompt("Enter folder path to save articles to:", outputDir);
      if (custom) {
        setOutputDir(custom);
        setDirHandle(null);
      }
    }
  };

  const handlePasteGo = () => {
    const extracted = extractAllPmcids(pasteText);
    if (extracted.length === 0) {
      alert("No PMCIDs found in that text.");
      return;
    }
    setRows(extracted);
    setIsPasteModalOpen(false);
    setPasteText("");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    const nonBlank = rows.map((r) => r.trim()).filter(Boolean);
    if (nonBlank.length === 0) {
      setError("Please enter at least one PMCID or PMC article URL.");
      return;
    }

    const validPmcids: string[] = [];
    const invalid: string[] = [];

    for (const val of nonBlank) {
      try {
        const found = extractAllPmcids(val);
        if (found.length > 0) {
          validPmcids.push(...found);
        } else {
          validPmcids.push(normalizePmcid(val));
        }
      } catch {
        invalid.push(val);
      }
    }

    if (invalid.length > 0) {
      setError(
        `Invalid entry: ${invalid.join(", ")} (expected PMCID or PMC URL)`
      );
      return;
    }

    const uniquePmcids = Array.from(new Set(validPmcids));

    setLoading(true);
    setStatusText(`Fetching ${uniquePmcids.length} article(s)...`);
    setProgressPercent(20);

    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
      "http://localhost:8000";

    try {
      const res = await fetch(`${apiBase}/api/v1/pubmed/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pmcids: uniquePmcids,
          output_dir: outputDir.trim() || "output/pubmed",
        }),
      });

      if (!res.ok) {
        const errorDetail = await res.text();
        throw new Error(`Fetch failed (${res.status}): ${errorDetail}`);
      }

      const data: FetchResult = await res.json();

      if (dirHandle) {
        for (const item of data.saved) {
          if (item.data) {
            try {
              const fileHandle = await dirHandle.getFileHandle(`${item.id}.json`, {
                create: true,
              });
              const writable = await fileHandle.createWritable();
              await writable.write(JSON.stringify(item.data, null, 2));
              await writable.close();
            } catch (fileErr) {
              console.warn(`Could not save ${item.id}.json locally:`, fileErr);
            }
          }
        }
      }

      setProgressPercent(100);
      setResult(data);
      setStatusText(
        `Done: ${data.saved.length} saved, ${data.skipped.length} skipped, ${data.errors.length} errors.`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to fetch articles";
      setError(msg);
      setStatusText("Failed to complete request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pmc-modal-overlay" onClick={onClose}>
      <div
        className="pmc-modal-window"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pmc-modal-title"
      >
        <div className="pmc-modal-header">
          <h2 id="pmc-modal-title">PMC Article Fetcher</h2>
          <button
            type="button"
            className="pmc-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {isPasteModalOpen ? (
          <div className="pmc-paste-subview">
            <h3 className="pmc-subview-title">Paste a list of PMCIDs</h3>
            <p className="pmc-paste-hint">
              Paste PMCIDs or PMC URLs below. Any separator is fine — newlines,
              commas, spaces, or nothing at all.
            </p>
            <textarea
              className="pmc-paste-textarea"
              rows={8}
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="e.g. PMC1234567, https://pmc.ncbi.nlm.nih.gov/articles/PMC7654321/..."
              autoFocus
            />
            <div className="pmc-paste-actions">
              <button
                type="button"
                className="pmc-secondary-btn"
                onClick={() => setIsPasteModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pmc-primary-btn"
                onClick={handlePasteGo}
              >
                Go
              </button>
            </div>
          </div>
        ) : (
          <form className="pmc-modal-body" onSubmit={handleSubmit}>
            <label className="pmc-instruction-label">
              Enter one or more PMC article URLs or PMCIDs:
            </label>

            <div className="pmc-rows-container">
              {rows.map((rowVal, idx) => (
                <div key={idx} className="pmc-entry-row">
                  <input
                    type="text"
                    className="pmc-entry-input"
                    value={rowVal}
                    placeholder="e.g. PMC1234567 or article URL"
                    onChange={(e) => handleRowChange(idx, e.target.value)}
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="pmc-remove-row-btn"
                    onClick={() => handleRemoveRow(idx)}
                    disabled={rows.length <= 1 || loading}
                    title="Remove row"
                  >
                    <Minus size={14} />
                  </button>
                </div>
              ))}
            </div>

            <div className="pmc-row-toolbar">
              <button
                type="button"
                className="pmc-subtle-btn"
                onClick={handleAddRow}
                disabled={loading}
              >
                <Plus size={14} /> Add another
              </button>
              <button
                type="button"
                className="pmc-subtle-btn"
                onClick={() => setIsPasteModalOpen(true)}
                disabled={loading}
              >
                Paste a list...
              </button>
            </div>

            <div className="pmc-save-row">
              <label htmlFor="pmc-output-dir">Save to:</label>
              <input
                id="pmc-output-dir"
                type="text"
                className="pmc-save-input"
                value={outputDir}
                onChange={(e) => {
                  setOutputDir(e.target.value);
                  setDirHandle(null);
                }}
                disabled={loading}
              />
              <button
                type="button"
                className="pmc-subtle-btn pmc-browse-btn"
                onClick={handleBrowseDirectory}
                disabled={loading}
              >
                Browse...
              </button>
            </div>

            {error && <div className="pmc-error-banner">{error}</div>}

            {loading && (
              <div className="pmc-progress-wrap">
                <div
                  className="pmc-progress-bar"
                  style={{ width: `${progressPercent ?? 30}%` }}
                />
              </div>
            )}

            {statusText && (
              <div className="pmc-status-line">{statusText}</div>
            )}

            {result && result.saved.length > 0 && (
              <div className="pmc-results-list">
                <div className="pmc-results-summary">
                  Saved {result.saved.length} article(s) to{" "}
                  <code>
                    {dirHandle ? `[Local Folder] ${dirHandle.name}` : result.output_dir}
                  </code>
                </div>
                <ul>
                  {result.saved.slice(0, 5).map((s) => (
                    <li key={s.id}>
                      <strong>{s.id}</strong>: {s.title}
                    </li>
                  ))}
                  {result.saved.length > 5 && (
                    <li>...and {result.saved.length - 5} more</li>
                  )}
                </ul>
              </div>
            )}

            <div className="pmc-modal-footer">
              <button
                type="button"
                className="pmc-secondary-btn"
                onClick={onClose}
                disabled={loading}
              >
                Close
              </button>
              <button
                type="submit"
                className="pmc-primary-btn"
                disabled={loading}
              >
                {loading ? "Fetching..." : "Submit"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
