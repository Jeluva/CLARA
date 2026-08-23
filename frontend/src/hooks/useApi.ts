import { useEffect, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Fetch-on-mount hook with loading/error state. `fetcher` is expected to be a
 * stable reference (module-level API function) or a closure over `deps`, so
 * refetch only happens on `reload()` or when a `deps` entry changes (e.g. the
 * active portfolio) -- pass `deps` when the fetcher closes over something
 * that can change while the page stays mounted.
 * `reload()` re-runs it — handy after a mutation the page just made.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): ApiState<T> {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: string | null;
  }>({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: null });
    fetcher()
      .then((data) => {
        if (active) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (active)
          setState({
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : "Error desconocido",
          });
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, ...deps]);

  return { ...state, reload: () => setVersion((v) => v + 1) };
}
