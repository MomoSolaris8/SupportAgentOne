import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${backendApiUrl}/health`, {
      signal: AbortSignal.timeout(10_000)
    });
    const body = await response.text();
    return NextResponse.json({
      backendApiUrl,
      ok: response.ok,
      status: response.status,
      body
    });
  } catch (error) {
    return NextResponse.json(
      {
        backendApiUrl,
        ok: false,
        error: error instanceof Error ? error.message : "Unknown backend fetch error"
      },
      { status: 502 }
    );
  }
}
