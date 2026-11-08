/* Measures where the existing labels and dots actually sit, in svg user
   units, and writes data/map-obstacles.json. The label widths come from the
   font, so they cannot be worked out on paper - a headless browser is the
   only honest source. Re-run after adding or renaming any pin:

       node data/map-label-boxes.js            (serves the repo itself)
*/
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const TYPES = {'.html':'text/html','.js':'text/javascript','.css':'text/css',
               '.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml',
               '.ico':'image/x-icon','.webp':'image/webp'};
(async () => {
  const srv = http.createServer((req, res) => {
    const f = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(f, (e, d) => e ? (res.writeHead(404), res.end())
      : (res.writeHead(200, {'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream'}),
         res.end(d)));
  }).listen(0);
  const port = srv.address().port;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1512, height: 950 } });
  await p.goto(`http://127.0.0.1:${port}/neighborhoods.html`, { waitUntil: 'networkidle' });
  const out = await p.evaluate(() => {
    const r = { labels: [], dots: [] };
    document.querySelectorAll('.mp__pin:not(.mp__pin--list) .mp__lbl').forEach(t => {
      const bb = t.getBBox();
      r.labels.push({ t: t.textContent, x: bb.x, y: bb.y, w: bb.width, h: bb.height });
    });
    document.querySelectorAll('.mp__pin:not(.mp__pin--list) .mp__dot').forEach(c => {
      r.dots.push({ x: +c.getAttribute('cx'), y: +c.getAttribute('cy') });
    });
    return r;
  });
  fs.writeFileSync(path.join(ROOT, 'data/map-obstacles.json'), JSON.stringify(out, null, 1));
  console.log(`${out.labels.length} labels, ${out.dots.length} dots -> data/map-obstacles.json`);
  await b.close(); srv.close();
})();
