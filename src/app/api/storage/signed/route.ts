import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/api-config";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const path = searchParams.get("path") || "";
  const expires = searchParams.get("expires") || "";
  const token = searchParams.get("token") || "";

  const backendUrl = `${API_BASE_URL}/documents/storage/signed?path=${encodeURIComponent(path)}&expires=${expires}&token=${token}`;

  try {
    const res = await fetch(backendUrl);
    if (!res.ok) {
      return NextResponse.redirect(backendUrl);
    }
    const blob = await res.arrayBuffer();
    const contentType = res.headers.get("content-type") || "application/octet-stream";
    return new NextResponse(blob, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": res.headers.get("content-disposition") || "inline"
      }
    });
  } catch {
    return NextResponse.redirect(backendUrl);
  }
}
