import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (
    path.some(
      (p) =>
        !p || p === "." || p === ".." || p.includes("/") || p.includes("\\"),
    )
  )
    return NextResponse.json({ detail: "Geçersiz API yolu" }, { status: 400 });
  if (Number(request.headers.get("content-length") || 0) > 65536)
    return NextResponse.json(
      { detail: "İstek boyutu sınırı aşıldı" },
      { status: 413 },
    );
  const base = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
  const url = new URL("/api/" + path.map(encodeURIComponent).join("/"), base);
  url.search = request.nextUrl.search;
  try {
    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.text();
    if (body && new TextEncoder().encode(body).length > 65536)
      return NextResponse.json(
        { detail: "İstek boyutu sınırı aşıldı" },
        { status: 413 },
      );
    const headers = new Headers({ Accept: "application/json" });
    if (body) headers.set("Content-Type", "application/json");
    if (request.headers.has("authorization"))
      headers.set("Authorization", request.headers.get("authorization")!);
    const response = await fetch(url, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Yerel API bağlantısı kurulamadı. API servisini ve API_INTERNAL_URL ayarını kontrol edin.",
      },
      { status: 502 },
    );
  }
}
export { proxy as GET, proxy as POST };
