"use client";

import { useEffect, useState } from "react";
import { Check, ShieldCheck } from "lucide-react";

import { useApp } from "@/components/app-provider";
import { Settings } from "@/lib/types";

export default function SettingsPage() {
  const { settings, setSettings } = useApp();

  const [draft, setDraft] = useState<Settings>(settings);
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const update = <K extends keyof Settings>(
    key: K,
    value: Settings[K]
  ) => {
    setDraft((old) => ({
      ...old,
      [key]: value,
    }));
  };

  async function save() {
    try {
      setSaving(true);
      setStatus("");

      await setSettings(draft);

      setStatus("Preferences saved");
    } catch (e) {
      setStatus(
        e instanceof Error ? e.message : "Failed to save"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="content-page settings-page">
      <header className="content-header">
        <span className="eyebrow">WORKSPACE</span>

        <h1>Settings</h1>

        <p>
          Personalize your research environment and conversation
          preferences.
        </p>
      </header>

      <section className="settings-section">
        <h2>Profile</h2>

        <p className="section-description">
          Used in the workspace display. Authentication and identity
          will be managed by FastAPI later.
        </p>

        <label className="field">
          Display name

          <input
            value={draft.clinicianName}
            onChange={(e) =>
              update("clinicianName", e.target.value)
            }
            maxLength={90}
          />
        </label>

        <label className="field">
          Clinical focus

          <input
            value={draft.specialty}
            onChange={(e) =>
              update("specialty", e.target.value)
            }
            maxLength={90}
          />
        </label>
      </section>

      <section className="settings-section">
        <h2>Appearance</h2>

        <label className="field">
          Theme

          <select
            value={draft.theme}
            onChange={(e) =>
              update(
                "theme",
                e.target.value as Settings["theme"]
              )
            }
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">Follow system</option>
          </select>
        </label>
      </section>

      <section className="settings-section">
        <h2>Chat behavior</h2>

        <label className="setting-toggle">
          <span>
            <strong>Enter to send</strong>

            <small>
              Use Shift + Enter to insert a new line.
            </small>
          </span>

          <input
            type="checkbox"
            checked={draft.enterToSend}
            onChange={(e) =>
              update("enterToSend", e.target.checked)
            }
          />
        </label>

        <label className="setting-toggle">
          <span>
            <strong>Show clinical disclaimer</strong>

            <small>
              Display a decision-support reminder beneath the chat.
            </small>
          </span>

          <input
            type="checkbox"
            checked={draft.showDisclaimer}
            onChange={(e) =>
              update("showDisclaimer", e.target.checked)
            }
          />
        </label>
      </section>

      <div className="settings-actions">
        <button
          className="primary-btn"
          disabled={saving}
          onClick={() => void save()}
        >
          <Check size={16} />
          {saving ? "Saving…" : "Save changes"}
        </button>

        {status && (
          <span role="status">
            {status}
          </span>
        )}
      </div>

      <div className="privacy-note">
        <ShieldCheck size={17} />

        <p>
          Demo mode stores conversations and preferences in this
          browser. It is not suitable for real patient-identifiable
          information. Use an authenticated, secured backend before
          handling PHI.
        </p>
      </div>
    </div>
  );
}