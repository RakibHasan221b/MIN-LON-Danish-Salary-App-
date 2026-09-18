/** Local-only persistence of the user's last-used inputs. No backend
 * persistence, no accounts — per the approved V1 scope. Wrapped in
 * try/catch since localStorage can throw or be unavailable. */

const KEY = "min-loen:last-inputs:v1";

export function saveLastInputs(data: unknown): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // ignore — local convenience only, never load-bearing
  }
}

export function loadLastInputs<T>(): T | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}
