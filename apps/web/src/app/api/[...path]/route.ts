import { proxyRequest } from "@/lib/proxy";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const suffix = path.map((segment) => encodeURIComponent(segment)).join("/");
  return proxyRequest(request, `/api/${suffix}`);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
