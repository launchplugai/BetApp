import { createReadStream, existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const staticDir = join(root, "static");
const port = Number(process.env.PORT || 3000);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

function safePath(urlPath) {
  const requested = urlPath === "/" ? "/index.html" : urlPath;
  const withHtmlFallback = extname(requested) ? requested : `${requested}.html`;
  const normalized = normalize(requested).replace(/^(\.\.[/\\])+/, "");
  const normalizedWithHtmlFallback = normalize(withHtmlFallback).replace(/^(\.\.[/\\])+/, "");
  const directPath = join(staticDir, normalized);
  if (existsSync(directPath)) {
    return directPath;
  }

  return join(staticDir, normalizedWithHtmlFallback);
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
    const filePath = safePath(url.pathname);

    if (!filePath.startsWith(staticDir) || !existsSync(filePath)) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }

    if (extname(filePath) === ".html") {
      const html = await readFile(filePath, "utf8");
      res.writeHead(200, { "Content-Type": contentTypes[".html"] });
      res.end(html);
      return;
    }

    res.writeHead(200, {
      "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream",
    });
    createReadStream(filePath).pipe(res);
  } catch (error) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(error instanceof Error ? error.message : "Server error");
  }
});

server.listen(port, () => {
  console.log(`BetApp frontend fallback server listening on http://localhost:${port}`);
});
