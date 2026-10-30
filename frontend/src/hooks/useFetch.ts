import { useCallback, useEffect, useRef, useState } from "react";
import { describeError } from "../api/errors";

/**
 * Runs an async loader and exposes the three states every screen must handle:
 * loading, error, data. Re-runs when `deps` change; `reload()` forces a refresh.
 */
export function useFetch<T>(loader: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false; // ignore results of an outdated request (e.g. user changed filters quickly)
    setLoading(true);
    setError(null);
    loaderRef
      .current()
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(describeError(err).message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload, setData };
}
