import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { timingSafeEqual, createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../website", import.meta.url));
const key = process.env.PI_REVIEW_KEY_FILE
  ? (await readFile(process.env.PI_REVIEW_KEY_FILE, "utf8")).trim()
  : null;
const equal = (a, b) => {
  const x = Buffer.from(a),
    y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".zip": "application/zip",
  ".sol": "text/plain; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/plain; charset=utf-8",
};
http
  .createServer(async (req, res) => {
    res.setHeader("X-Robots-Tag", "noindex, nofollow");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Cache-Control", "private, no-store");
    if (!["GET", "HEAD"].includes(req.method)) {
      res.writeHead(405);
      return res.end("Read-only preview");
    }
    let u;
    try {
      u = new URL(req.url, "http://localhost");
    } catch {
      res.writeHead(400);
      return res.end();
    }
    // A content-addressed link grants access only to this exact review archive.
    // It does not expose the preview key or unlock any other route.
    if (/^\/download\/[a-f0-9]{64}$/.test(u.pathname)) {
      try {
        const bytes = await readFile(
          resolve(root, "review/holdpi-bnb-review.zip"),
        );
        const digest = createHash("sha256").update(bytes).digest("hex");
        if (!equal(u.pathname.slice(10), digest)) {
          res.writeHead(404);
          return res.end();
        }
        res.setHeader("Content-Type", "application/zip");
        res.setHeader("Content-Length", bytes.length);
        res.setHeader(
          "Content-Disposition",
          'attachment; filename="holdpi-bnb-review.zip"',
        );
        res.writeHead(200);
        return res.end(req.method === "HEAD" ? undefined : bytes);
      } catch {
        res.writeHead(404);
        return res.end();
      }
    }
    if (key) {
      if (u.pathname.startsWith("/open/") && equal(u.pathname.slice(6), key)) {
        res.setHeader(
          "Set-Cookie",
          `pi_review=${key}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`,
        );
        res.writeHead(303, {
          Location: ["/docs", "/brandbook"].includes(u.searchParams.get("to"))
            ? u.searchParams.get("to")
            : "/",
        });
        return res.end();
      }
      const cookie =
        (req.headers.cookie || "")
          .split(";")
          .map((x) => x.trim())
          .find((x) => x.startsWith("pi_review="))
          ?.slice(10) || "";
      if (!equal(cookie, key)) {
        res.writeHead(401);
        return res.end("Use the private review link.");
      }
    }
    let p;
    try {
      p = decodeURIComponent(u.pathname);
    } catch {
      res.writeHead(400);
      return res.end();
    }
    if (p === "/") p = "/index.html";
    if (!extname(p)) p += ".html";
    const target = resolve(root, "." + p);
    if (!target.startsWith(root + sep)) {
      res.writeHead(403);
      return res.end();
    }
    try {
      const s = await stat(target);
      if (!s.isFile()) throw Error("not file");
      res.setHeader(
        "Content-Type",
        mime[extname(target)] || "application/octet-stream",
      );
      res.setHeader("Content-Length", s.size);
      if (target.endsWith(".zip"))
        res.setHeader(
          "Content-Disposition",
          `attachment; filename="${target.split(sep).pop()}"`,
        );
      res.writeHead(200);
      res.end(req.method === "HEAD" ? undefined : await readFile(target));
    } catch {
      res.writeHead(404);
      res.end("Page not found");
    }
  })
  .listen(Number(process.env.PORT || 8188), "127.0.0.1", () =>
    console.log("HoldPI review server ready."),
  );
