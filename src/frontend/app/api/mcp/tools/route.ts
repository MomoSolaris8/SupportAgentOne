import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const requestTimeoutMs = 30_000;

export async function GET(request: Request) {
  let response: Response;

  try {
    response = await fetch(`${backendApiUrl}/mcp/tools`, {
      headers: {
        Cookie: request.headers.get("cookie") ?? ""
      },
      signal: AbortSignal.timeout(requestTimeoutMs)
    });
  } catch {
    return NextResponse.json({ detail: "Backend is not reachable" }, { status: 502 });
  }

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}
