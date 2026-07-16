import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const requestTimeoutMs = 60_000;

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

async function proxyAuth(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const body = request.method === "GET" ? undefined : await request.text();

  let response: Response;
  try {
    response = await fetch(`${backendApiUrl}/auth/${path.join("/")}`, {
      method: request.method,
      headers: {
        "Content-Type": request.headers.get("Content-Type") ?? "application/json",
        Cookie: request.headers.get("cookie") ?? ""
      },
      body,
      redirect: "manual",
      signal: AbortSignal.timeout(requestTimeoutMs)
    });
  } catch (error) {
    const message =
      error instanceof Error && error.name === "TimeoutError"
        ? "Backend request timed out"
        : "Backend is not reachable";

    return NextResponse.json(
      { detail: message },
      { status: error instanceof Error && error.name === "TimeoutError" ? 504 : 502 }
    );
  }

  const location = response.headers.get("location");
  if (location && response.status >= 300 && response.status < 400) {
    return NextResponse.redirect(location, response.status);
  }

  const responseBody = await response.text();
  const nextResponse = new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });

  const setCookie = response.headers.get("set-cookie");
  if (setCookie) {
    nextResponse.headers.set("Set-Cookie", setCookie);
  }
  return nextResponse;
}

export async function GET(request: Request, context: RouteContext) {
  return proxyAuth(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxyAuth(request, context);
}
