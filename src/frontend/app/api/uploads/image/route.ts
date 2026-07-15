import { NextResponse } from "next/server";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const response = await fetch(`${backendApiUrl}/uploads/image`, {
      method: "POST",
      headers: {
        Cookie: request.headers.get("cookie") ?? ""
      },
      body: formData
    });
    const body = await response.text();
    const contentType = response.headers.get("Content-Type") ?? "application/json";

    if (!response.ok && !contentType.includes("application/json")) {
      return NextResponse.json(
        { detail: body || `Backend upload failed with ${response.status}` },
        { status: response.status }
      );
    }

    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": contentType
      }
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? `Upload proxy failed: ${error.message}`
            : "Upload proxy failed."
      },
      { status: 502 }
    );
  }
}
