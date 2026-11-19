const json=(data,status=200,headers={})=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store',...headers}});
const valid=(s)=>typeof s==='string'&&/^[a-z0-9-]{1,100}$/.test(s);
const cookieName='jl_visitor';
function getCookie(request){const match=(request.headers.get('Cookie')||'').match(/(?:^|;\s*)jl_visitor=([a-f0-9]{32})/);return match?.[1]||null;}
async function aggregate(db,type,slug,visitor){
 const likes=await db.prepare("SELECT COUNT(*) AS n FROM engagement WHERE kind='like' AND content_type=? AND slug=?").bind(type,slug).first();
 const votes=await db.prepare("SELECT COUNT(*) AS n, AVG(value) AS avg FROM engagement WHERE kind='rating' AND content_type='review' AND slug=?").bind(slug).first();
 const mine=visitor?await db.prepare("SELECT kind,value FROM engagement WHERE content_type=? AND slug=? AND visitor=?").bind(type,slug,visitor).all():{results:[]};
 return {likes:likes?.n||0,ratingCount:type==='review'?(votes?.n||0):0,ratingAverage:type==='review'&&votes?.n>=5?Math.round(votes.avg)/10:null,liked:mine.results.some(x=>x.kind==='like'),myRating:mine.results.find(x=>x.kind==='rating')?.value/10||null};
}
export async function onRequestGet({request,env}){
 if(!env.ENGAGEMENT_DB)return json({error:'Engagement database not configured'},503);
 const u=new URL(request.url),type=u.searchParams.get('type'),slug=u.searchParams.get('slug');
 if(!['article','review','ranking'].includes(type)||!valid(slug))return json({error:'Invalid content'},400);
 try{return json(await aggregate(env.ENGAGEMENT_DB,type,slug,getCookie(request)))}catch{return json({error:'Engagement data unavailable'},503)}
}
export async function onRequestPost({request,env}){
 if(!env.ENGAGEMENT_DB)return json({error:'Engagement database not configured'},503);
 const origin=request.headers.get('Origin');if(origin&&origin!==new URL(request.url).origin)return json({error:'Invalid origin'},403);
 if(Number(request.headers.get('Content-Length')||0)>2048)return json({error:'Payload too large'},413);
 let body;try{body=await request.json()}catch{return json({error:'Invalid JSON'},400)}
 const {type,slug,kind,value}=body||{};
 if(!['article','review','ranking'].includes(type)||!valid(slug)||!['like','rating'].includes(kind))return json({error:'Invalid request'},400);
 if(kind==='rating'&&(type!=='review'||!Number.isInteger(value)||value<10||value>100))return json({error:'Rating must be 1.0–10.0'},400);
 if(kind==='like'&&typeof value!=='boolean')return json({error:'Invalid like'},400);
 const visitor=getCookie(request)||Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
 const cookie=`${cookieName}=${visitor}; Path=/; Max-Age=31536000; Secure; HttpOnly; SameSite=Lax`;
 try{
  if(kind==='like'&&!value)await env.ENGAGEMENT_DB.prepare("DELETE FROM engagement WHERE kind='like' AND content_type=? AND slug=? AND visitor=?").bind(type,slug,visitor).run();
  else await env.ENGAGEMENT_DB.prepare("INSERT INTO engagement(kind,content_type,slug,visitor,value) VALUES(?,?,?,?,?) ON CONFLICT(kind,content_type,slug,visitor) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP").bind(kind,type,slug,visitor,kind==='like'?1:value).run();
  return json(await aggregate(env.ENGAGEMENT_DB,type,slug,visitor),200,{'Set-Cookie':cookie});
 }catch{return json({error:'Could not save your vote'},503)}
}
