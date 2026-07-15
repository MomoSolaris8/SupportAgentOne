import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{
    threadId: string;
    messageId: string;
  }>;
};

export async function PATCH(request: Request, context: RouteContext) {
  const { threadId, messageId } = await context.params;
  const response = await fetch(`${backendApiUrl}/threads/${threadId}/messages/${messageId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Cookie: request.headers.get("cookie") ?? ""
    },
    body: await request.text()
  });
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}

export async function DELETE(request: Request, context: RouteContext) {
  const { threadId, messageId } = await context.params;
  const response = await fetch(`${backendApiUrl}/threads/${threadId}/messages/${messageId}`, {
    method: "DELETE",
    headers: {
      Cookie: request.headers.get("cookie") ?? ""
    }
  });
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}
