import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiError, apiGet, apiPost, apiDelete } from "@/lib/api";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

describe("apiGet", () => {
  it("fetches JSON from the correct path", async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ value: 42 }));
    const result = await apiGet<{ value: number }>("/test");
    expect(mockFetch).toHaveBeenCalledWith("/api/test", undefined);
    expect(result.value).toBe(42);
  });

  it("throws ApiError on non-ok response with detail", async () => {
    mockFetch.mockReturnValueOnce(
      Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Not found" }),
      }),
    );
    await expect(apiGet("/missing")).rejects.toThrow(ApiError);
    await expect(apiGet("/missing")).rejects.toThrow();
  });

  it("throws ApiError on network failure", async () => {
    mockFetch.mockReturnValueOnce(Promise.reject(new TypeError("Failed to fetch")));
    await expect(apiGet("/offline")).rejects.toThrow(ApiError);
  });
});

describe("apiPost", () => {
  it("sends JSON body with correct headers", async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ id: 1 }));
    await apiPost("/items", { name: "test" });
    expect(mockFetch).toHaveBeenCalledWith("/api/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"name":"test"}',
    });
  });
});

describe("apiDelete", () => {
  it("sends DELETE and handles 204", async () => {
    mockFetch.mockReturnValueOnce(
      Promise.resolve({ ok: true, status: 204 }),
    );
    const result = await apiDelete("/items/1");
    expect(result).toBeUndefined();
  });
});
