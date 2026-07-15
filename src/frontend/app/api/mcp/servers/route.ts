import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const response = await fetch(`${backendApiUrl}/mcp/servers`, {
    headers: { Cookie: request.headers.get("cookie") ?? "" }
  });
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" }
  });
}
