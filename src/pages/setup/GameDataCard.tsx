import { useEffect, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { open } from "@tauri-apps/plugin-dialog"
import { AlertTriangle, CheckCircle, Loader2, XCircle } from "lucide-react"
import { api, inTauri } from "@/lib/api"
import type { ExtractJob, ExtractSettings } from "@/lib/types"
import { Button } from "@/components/ui/button"

const STATUS_KEY = ["extract-status"]

/** Props for PathField. */
interface PathFieldProps {
  /** Label shown above the input. */
  label: string
  /** The saved value the input starts from. Callers key the field on it so a new saved value resets the draft. */
  value: string
  /** Optional note shown beside the label, such as "Detected". */
  badge?: string
  /** Optional hint line under the input. */
  hint?: string
  /** Disables editing while a job runs. */
  disabled: boolean
  /** Opens a native picker. Null when not running inside Tauri. */
  onBrowse: (() => Promise<string | null>) | null
  /** Saves a new value. Called on blur when the text changed, and after a Browse pick. */
  onSave: (value: string) => void
}

/**
 * One editable path with an optional Browse button.
 * @param props - See `PathFieldProps`.
 * @returns The labelled input row.
 */
function PathField({ label, value, badge, hint, disabled, onBrowse, onSave }: PathFieldProps) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState(value)

  const browse = async () => {
    const picked = await onBrowse?.()
    if (picked) {
      setDraft(picked)
      onSave(picked)
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-[#b3b3b3] flex items-center gap-2">
        {label}
        {badge && <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#282828] text-[#c084fc]">{badge}</span>}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          disabled={disabled}
          spellCheck={false}
          onChange={e => setDraft(e.target.value)}
          onBlur={() => { if (draft.trim() !== value) onSave(draft.trim()) }}
          className="flex-1 min-w-0 bg-[#121212] border border-[#282828] rounded px-2 py-1.5 text-xs text-[#ffffff] font-mono disabled:opacity-50"
        />
        {onBrowse && (
          <Button size="sm" variant="outline" disabled={disabled} onClick={browse} className="border-[#3f3f3f] text-[#b3b3b3] hover:text-[#ffffff] shrink-0">
            {t("setup.gameData.browse")}
          </Button>
        )}
      </div>
      {hint && <p className="text-[11px] text-[#666666]">{hint}</p>}
    </div>
  )
}

/**
 * Picks a file or folder with the native dialog.
 * @param directory - Pick a folder instead of a file.
 * @param current - Where the dialog starts.
 * @param filter - File filter as a display name and extension list, ignored for folders.
 * @returns The chosen path, or null if the user cancelled.
 */
async function pickPath(directory: boolean, current: string, filter?: { name: string; extensions: string[] }): Promise<string | null> {
  const picked = await open({ directory, multiple: false, defaultPath: current || undefined, filters: filter && !directory ? [filter] : undefined })
  return typeof picked === "string" ? picked : null
}

/**
 * The text colour for a finished job's message.
 * @param job - The job.
 * @returns A Tailwind text class.
 */
function messageClass(job: ExtractJob): string {
  if (job.state === "ok") return "text-green-500"
  if (job.state === "cancelled") return "text-[#b3b3b3]"
  return "text-[#f3727f]"
}

/**
 * Setup page card that extracts the game's client data with ChaosZeroNightmareRipper-CLI.exe, and in dev mode runs add_character.py on it.
 * @returns The card, or nothing until the first status arrives.
 */
export function GameDataCard() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const logRef = useRef<HTMLPreElement>(null)

  const { data: status } = useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.extractStatus(),
    refetchInterval: query => (query.state.data?.job?.state === "running" ? 1000 : false),
  })

  const refresh = () => qc.invalidateQueries({ queryKey: STATUS_KEY })
  const saveMutation = useMutation({ mutationFn: (body: Partial<ExtractSettings>) => api.saveExtractConfig(body), onSuccess: refresh })
  const startMutation = useMutation({ mutationFn: () => api.startExtract(), onSuccess: refresh })
  const cancelMutation = useMutation({ mutationFn: () => api.cancelExtract(), onSuccess: refresh })
  const applyMutation = useMutation({ mutationFn: (dryRun: boolean) => api.applyCharacters(dryRun), onSuccess: refresh })

  const job = status?.job ?? null
  const logLength = job?.log.length ?? 0

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLength])

  if (!status) return null

  const { settings } = status
  const running = job?.state === "running"
  const canBrowse = inTauri()
  const save = (key: keyof ExtractSettings) => (value: string) => saveMutation.mutate({ [key]: value })
  const actionError = [saveMutation, startMutation, cancelMutation, applyMutation].find(m => m.isError)?.error
  const dryRunDone = job?.kind === "dry_run" && job.state === "ok"

  return (
    <div className="p-4 rounded-lg bg-[#181818] border border-[#282828] flex flex-col gap-3">
      <div>
        <p className="text-[#ffffff] font-medium text-sm flex items-center gap-2">
          {t("setup.gameData.title")}
          {status.dev_mode && <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#282828] text-[#b3b3b3]">{t("setup.gameData.devOnly")}</span>}
        </p>
        <p className="text-[#b3b3b3] text-xs mt-0.5">{t("setup.gameData.detail")}</p>
      </div>

      <PathField
        key={settings.pack_path}
        label={t("setup.gameData.pack")}
        value={settings.pack_path}
        badge={settings.pack_path && settings.pack_path === status.detected_pack_path ? t("setup.gameData.detected") : undefined}
        hint={settings.pack_path ? undefined : t("setup.gameData.packMissing")}
        disabled={running}
        onBrowse={canBrowse ? () => pickPath(false, settings.pack_path, { name: "Game archive", extensions: ["ssra", "pack"] }) : null}
        onSave={save("pack_path")}
      />
      <PathField
        key={settings.cli_path}
        label={t("setup.gameData.cli")}
        value={settings.cli_path}
        hint={t("setup.gameData.cliHint")}
        disabled={running}
        onBrowse={canBrowse ? () => pickPath(false, settings.cli_path, { name: "ChaosZeroNightmareRipper-CLI", extensions: ["exe"] }) : null}
        onSave={save("cli_path")}
      />
      <PathField
        key={settings.out_dir}
        label={t("setup.gameData.outDir")}
        value={settings.out_dir}
        disabled={running}
        onBrowse={canBrowse ? () => pickPath(true, settings.out_dir) : null}
        onSave={save("out_dir")}
      />

      {status.env_override && (
        <p className="text-xs text-[#fbbf24] flex items-start gap-1.5">
          <AlertTriangle size={14} className="shrink-0 mt-px" />
          {t("setup.gameData.envOverride", { path: status.env_override })}
        </p>
      )}

      <p className="text-xs text-[#b3b3b3] flex items-start gap-1.5 break-all">
        {status.active_ready
          ? <CheckCircle size={14} className="text-green-500 shrink-0 mt-px" />
          : <XCircle size={14} className="text-red-500 shrink-0 mt-px" />}
        {status.active_ready ? t("setup.gameData.active", { path: status.active_client_dir }) : t("setup.gameData.activeMissing")}
      </p>

      <div className="flex flex-wrap gap-2">
        {running ? (
          <Button size="sm" variant="outline" onClick={() => cancelMutation.mutate()} className="border-[#3f3f3f] text-[#b3b3b3] hover:text-[#f3727f] hover:border-[#f3727f]">
            {t("setup.gameData.cancel")}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={() => startMutation.mutate()}
            disabled={!settings.cli_path || !settings.pack_path || startMutation.isPending}
            className="bg-[#c084fc] hover:bg-[#9333ea] text-white"
          >
            {t("setup.gameData.extract")}
          </Button>
        )}
        {status.dev_mode && !running && (
          <Button size="sm" variant="outline" onClick={() => applyMutation.mutate(true)} className="border-[#3f3f3f] text-[#b3b3b3] hover:text-[#ffffff]">
            {t("setup.gameData.recheck")}
          </Button>
        )}
        {status.dev_mode && dryRunDone && (
          <Button size="sm" onClick={() => applyMutation.mutate(false)} title={t("setup.gameData.applyHint")} className="bg-[#c084fc] hover:bg-[#9333ea] text-white">
            {t("setup.gameData.apply")}
          </Button>
        )}
      </div>

      {actionError != null && <p className="text-[#f3727f] text-xs">{actionError instanceof Error ? actionError.message : t("common.unexpectedError")}</p>}

      {job && (
        <div className="flex flex-col gap-1.5">
          {running && (
            <p className="text-xs text-[#b3b3b3] flex items-center gap-1.5">
              <Loader2 size={14} className="animate-spin shrink-0" />
              {job.progress || t("setup.gameData.extracting")}
            </p>
          )}
          <pre ref={logRef} className="max-h-56 overflow-auto rounded-lg bg-[#0d0d0d] border border-[#282828] p-3 font-mono text-[11px] leading-relaxed text-[#b3b3b3] whitespace-pre-wrap break-all">
            {job.log.join("\n")}
          </pre>
          {job.message && <p className={`text-xs ${messageClass(job)}`}>{job.message}</p>}
        </div>
      )}
    </div>
  )
}
