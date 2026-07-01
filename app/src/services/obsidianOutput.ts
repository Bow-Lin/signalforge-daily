const OBSIDIAN_DIGEST_FOLDER = "SignalForge Daily";

export function buildObsidianOutputPath(vaultPath: string): string {
  const trimmed = vaultPath.trim();
  if (!trimmed) return "";
  const separator = trimmed.includes("\\") ? "\\" : "/";
  const base = trimmed.replace(/[\\/]+$/, "");
  return `${base}${separator}${OBSIDIAN_DIGEST_FOLDER}`;
}
