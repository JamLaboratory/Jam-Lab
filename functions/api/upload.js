// Same-origin Cloudflare Pages Function. The private upload key is provided by the
// editor for each upload and forwarded only server-to-server to the existing Worker.
// No secret is embedded in client code or stored in the browser.
export async function onRequestPost({ request }) {
  const auth = request.headers.get('Authorization') || '';
  const type = (request.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  if (!/^Bearer .+/.test(auth)) return new Response(JSON.stringify({error:'Missing upload key'}),{status:401,headers:{'Content-Type':'application/json'}});
  if (!['image/jpeg','image/png','image/webp'].includes(type)) return new Response(JSON.stringify({error:'Unsupported image type'}),{status:415,headers:{'Content-Type':'application/json'}});
  const size = Number(request.headers.get('Content-Length') || 0);
  if (size > 10 * 1024 * 1024) return new Response(JSON.stringify({error:'Image too large'}),{status:413,headers:{'Content-Type':'application/json'}});
  try {
    const upstream = await fetch('https://jam-lab-uploader.nickwalsh1125.workers.dev/upload', {
      method:'POST',
      headers:{Authorization:auth,'Content-Type':type},
      body:request.body
    });
    return new Response(upstream.body,{status:upstream.status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
  } catch {
    return new Response(JSON.stringify({error:'Artwork upload service unavailable'}),{status:502,headers:{'Content-Type':'application/json'}});
  }
}
