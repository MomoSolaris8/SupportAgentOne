import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const requestTimeoutMs = 60_000;

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

async function proxyClaimRequest(request: Request, context: RouteContext) {
  const { path = [] } = await context.params;
  const suffix = path.length ? `/${path.map(encodeURIComponent).join("/")}` : "";
  const body = request.method === "GET" ? undefined : await request.text();

  let response: Response;
  try {
    response = await fetch(`${backendApiUrl}/claims${suffix}`, {
      method: request.method,
      headers: {
        "Content-Type": request.headers.get("Content-Type") ?? "application/json",
        Cookie: request.headers.get("cookie") ?? ""
      },
      body,
      signal: AbortSignal.timeout(requestTimeoutMs)
    });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    return NextResponse.json(
      { detail: timedOut ? "Backend request timed out" : "Backend is not reachable" },
      { status: timedOut ? 504 : 502 }
    );
  }

  return new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}

export async function GET(request: Request, context: RouteContext) {
  return proxyClaimRequest(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxyClaimRequest(request, context);
}
