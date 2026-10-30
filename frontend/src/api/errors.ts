import axios from "axios";

export interface DescribedError {
  message: string;
  fields: Record<string, string>; // field name -> first message
  status: number | null;
}

/**
 * Turns anything thrown by an API call into something a component can show.
 * It separates the three very different failures people confuse:
 *   1. No response at all  -> network down, wrong URL/port, backend not running, or a CORS block
 *   2. Response, not our JSON shape -> proxy/HTML error page, Django debug page (500)
 *   3. Response with {"error": {...}} -> a deliberate API error (400/401/403/404/...)
 */
export function describeError(err: unknown): DescribedError {
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      return {
        status: null,
        fields: {},
        message:
          "Cannot reach the server. Check that the backend is running, the API URL is correct, and the browser console for a CORS error.",
      };
    }
    const body = err.response.data as { error?: { message?: string; fields?: Record<string, unknown> } } | string | undefined;
    if (body && typeof body === "object" && body.error) {
      const fields: Record<string, string> = {};
      for (const [name, value] of Object.entries(body.error.fields ?? {})) {
        fields[name] = Array.isArray(value) ? String(value[0]) : String(value);
      }
      return { status: err.response.status, fields, message: body.error.message ?? "Request failed." };
    }
    return { status: err.response.status, fields: {}, message: `Unexpected server response (HTTP ${err.response.status}). See the Network tab.` };
  }
  return { status: null, fields: {}, message: err instanceof Error ? err.message : "Something went wrong." };
}
