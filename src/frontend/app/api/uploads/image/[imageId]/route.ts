import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{
    imageId: string;
  }>;
};

export async function GET(request: Request, context: RouteContext) {
  try {
    const { imageId } = await context.params;
    const response = await fetch(`${backendApiUrl}/uploads/image/${imageId}`, {
      headers: {
        Cookie: request.headers.get("cookie") ?? ""
      }
    });
    const body = await response.arrayBuffer();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/octet-stream"
      }
    });
  } catch {
    return new NextResponse(null, { status: 502 });
  }
}
