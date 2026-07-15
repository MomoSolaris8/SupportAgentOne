import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";
const requestTimeoutMs = 60_000;

type RouteContext = {
  params: Promise<{
    threadId: string;
  }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { threadId } = await context.params;

  let response: Response;
  try {
    response = await fetch(
      `${backendApiUrl}/threads/${encodeURIComponent(threadId)}/messages`,
      {
        method: "GET",
        headers: {
          Cookie: request.headers.get("cookie") ?? ""
        },
        signal: AbortSignal.timeout(requestTimeoutMs)
      }
    );
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

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}
