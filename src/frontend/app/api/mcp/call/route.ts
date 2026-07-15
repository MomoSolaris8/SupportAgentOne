import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const requestTimeoutMs = 60_000;

export async function POST(request: Request) {
  const payload = await request.json();
  let response: Response;

  try {
    response = await fetch(`${backendApiUrl}/mcp/call`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: request.headers.get("cookie") ?? ""
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(requestTimeoutMs)
    });
  } catch (error) {
    const message =
      error instanceof Error && error.name === "TimeoutError"
        ? "Tool call timed out"
        : "Backend is not reachable";
    return NextResponse.json(
      { detail: message },
      { status: error instanceof Error && error.name === "TimeoutError" ? 504 : 502 }
    );
  }

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}
