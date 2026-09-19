import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/api-config";

import pathMod from "path";
import fs from "fs";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const rawPath = searchParams.get("path") || "";
  const expires = searchParams.get("expires") || "";
  const token = searchParams.get("token") || "";

  const filename = pathMod.basename(rawPath);
  const ext = pathMod.extname(filename).toLowerCase();
  const contentTypeMap: Record<string, string> = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg"
  };
  const mimeType = contentTypeMap[ext] || "application/octet-stream";

  // 1. Check local static public demo file first for instant zero-latency preview
  try {
    const demoDir = pathMod.join(process.cwd(), "public", "demo");
    const demoPath = pathMod.join(demoDir, filename);
    if (fs.existsSync(demoPath)) {
      const fileBuffer = fs.readFileSync(demoPath);
      return new NextResponse(fileBuffer, {
        headers: {
          "Content-Type": mimeType,
          "Content-Disposition": `inline; filename="${filename}"`
        }
      });
    }
  } catch (err) {
    // Proceed to backend fetch
  }

  // 2. Fetch from backend streaming endpoint
  const backendBase = process.env.NEXT_PUBLIC_API_URL || "https://hospital-records-system.onrender.com";
  const backendUrl = `${backendBase}/documents/storage/signed?path=${encodeURIComponent(rawPath)}&expires=${expires}&token=${token}`;

  try {
    const res = await fetch(backendUrl);
    if (res.ok) {
      const blob = await res.arrayBuffer();
      const resContentType = res.headers.get("content-type") || mimeType;
      return new NextResponse(blob, {
        headers: {
          "Content-Type": resContentType,
          "Content-Disposition": res.headers.get("content-disposition") || `inline; filename="${filename}"`
        }
      });
    }
  } catch (err) {
    console.error("Backend streaming fetch error:", err);
  }

  // 3. Graceful fallback redirect to static demo path
  return NextResponse.redirect(new URL(`/demo/${filename}`, request.url));
}
