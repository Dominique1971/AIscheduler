import { Failure, command, projectSnapshot } from "./contract.mjs";
import page from "./page.html";
import script from "./app.txt";
import styles from "./style.css";

const clock = () => Math.floor(Date.now()/1000);
const token = () => Array.from(crypto.getRandomValues(new Uint8Array(32)),n=>n.toString(16).padStart(2,"0")).join("");
export async function sha(value) { return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value))),n=>n.toString(16).padStart(2,"0")).join(""); }
const json = (value,status=200,headers={}) => Response.json(value,{status,headers});
async function objectBody(request,limit=16384) {
  const reader=request.body?.getReader();
  if (!reader) throw new Failure(400,"body_required");
  const chunks=[];let size=0;
  for (;;) { const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw new Failure(413,"request_too_large");}chunks.push(value); }
  const bytes=new Uint8Array(size);let pos=0;for(const chunk of chunks){bytes.set(chunk,pos);pos+=chunk.length;}
  let value;try{value=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));}catch{throw new Failure(400,"invalid_json");}
  if (!value || typeof value!=="object" || Array.isArray(value)) throw new Failure(422,"object_required");
  return value;
}
function config(env,url) {
  const local=env.DEV_MODE==="local-only" && ["127.0.0.1","localhost"].includes(url.hostname);
  if (url.origin!==env.APP_ORIGIN || !local && url.protocol!=="https:") throw new Failure(503,"origin_not_configured");
  const idConfigured=typeof env.OWNER_SITE_USER_ID==="string" && env.OWNER_SITE_USER_ID.length>=8;
  const emailConfigured=typeof env.OWNER_SITE_EMAIL==="string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(env.OWNER_SITE_EMAIL) && env.OWNER_SITE_EMAIL===env.OWNER_SITE_EMAIL.toLowerCase();
  if (idConfigured===emailConfigured ||
      typeof env.AGENT_TOKEN!=="string" || env.AGENT_TOKEN.length<43 ||
      typeof env.OWNER_TOTP_SECRET!=="string" || !/^[A-Z2-7]{32,}$/.test(env.OWNER_TOTP_SECRET)) throw new Failure(503,"configuration_required");
  return {local};
}
async function audit(env,actor,kind,commandId=null,detail={}) {
  await env.SCHEDULER_REMOTE.prepare("INSERT INTO audit(at,actor,kind,command_id,detail) VALUES(?,?,?,?,?)").bind(clock(),actor,kind,commandId,JSON.stringify(detail)).run();
}
async function rate(env,key,limit,seconds) {
  const now=clock();const bucket=Math.floor(now/seconds);
  const row=await env.SCHEDULER_REMOTE.prepare("INSERT INTO rate_limits(key,count,expires) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1 RETURNING count").bind(key+":"+bucket,now+seconds).first();
  if(row.count>limit)throw new Failure(429,"rate_limited");
}
function owner(request,env) {
  // Sites dispatch owns these headers. Private audience is still required at the platform edge.
  const id=request.headers.get("oai-authenticated-user-id");
  const email=request.headers.get("oai-authenticated-user-email")?.toLowerCase();
  if (env.OWNER_SITE_USER_ID) {
    if (!id || id!==env.OWNER_SITE_USER_ID) throw new Failure(403,"owner_required");
    return "site:"+id;
  }
  if (!email || email!==env.OWNER_SITE_EMAIL) throw new Failure(403,"owner_required");
  return "email:"+email;
}
function decodeBase32(value) {
  let bits=0, buffer=0; const bytes=[];
  for(const letter of value){const digit="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".indexOf(letter);if(digit<0)throw new Failure(503,"invalid_mfa_secret");buffer=(buffer<<5)|digit;bits+=5;if(bits>=8){bits-=8;bytes.push((buffer>>bits)&255);}}
  return Uint8Array.from(bytes);
}
async function totp(secret,counter) {
  const key=await crypto.subtle.importKey("raw",decodeBase32(secret),{name:"HMAC",hash:"SHA-1"},false,["sign"]);
  const value=new Uint8Array(8);let n=BigInt(counter);for(let i=7;i>=0;i--){value[i]=Number(n&255n);n>>=8n;}
  const mac=new Uint8Array(await crypto.subtle.sign("HMAC",key,value));const offset=mac[19]&15;
  const number=((mac[offset]&127)<<24)|(mac[offset+1]<<16)|(mac[offset+2]<<8)|mac[offset+3];
  return String(number%1000000).padStart(6,"0");
}
async function login(request,env,local) {
  const id=owner(request,env);
  await rate(env,"login:"+await sha(id+":"+(request.headers.get("cf-connecting-ip")??"local")),5,900);
  const body=await objectBody(request);
  if(!/^\d{6}$/.test(body.code??""))throw new Failure(422,"totp_required");
  const current=Math.floor(clock()/30);let matched=null;
  for(const step of [current-1,current,current+1]) if(await totp(env.OWNER_TOTP_SECRET,step)===body.code) matched=step;
  if(matched===null)throw new Failure(401,"invalid_totp");
  const used=await env.SCHEDULER_REMOTE.prepare("INSERT INTO mfa_counters(owner,last_counter) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET last_counter=excluded.last_counter WHERE excluded.last_counter>mfa_counters.last_counter RETURNING last_counter").bind(id,matched).first();
  if(!used)throw new Failure(401,"totp_replayed");
  const session=token(),csrf=token(),expires=clock()+900,role=env.REMOTE_CONTROL_ENABLED==="true"?"controller":"reader";
  await env.SCHEDULER_REMOTE.batch([
    env.SCHEDULER_REMOTE.prepare("INSERT INTO sessions VALUES(?,?,?,?,?)").bind(await sha(session),id,csrf,role,expires),
    env.SCHEDULER_REMOTE.prepare("INSERT INTO audit(at,actor,kind,detail) VALUES(?,?,?,?)").bind(clock(),id,"auth.login",JSON.stringify({factor:"totp",role}))
  ]);
  return json({role,csrf,expires_at:new Date(expires*1000).toISOString()},200,{"Set-Cookie":`scheduler_session=${session}; HttpOnly; ${local?"":"Secure; "}SameSite=Strict; Path=/; Max-Age=900`});
}
async function session(request,env) {
  const id=owner(request,env);
  const value=request.headers.get("cookie")?.split(";").map(x=>x.trim()).find(x=>x.startsWith("scheduler_session="))?.slice(18);
  if(!value || !/^[a-f0-9]{64}$/.test(value))throw new Failure(401,"sign_in_required");
  const row=await env.SCHEDULER_REMOTE.prepare("SELECT * FROM sessions WHERE hash=? AND expires>?").bind(await sha(value),clock()).first();
  if(!row || row.owner!==id)throw new Failure(401,"sign_in_required");
  return row;
}
async function agent(request,env) {
  const supplied=request.headers.get("authorization")??"";
  if(supplied.length>512 || await sha(supplied)!==await sha("Bearer "+env.AGENT_TOKEN))throw new Failure(401,"agent_auth_required");
}
async function route(request,env) {
  const url=new URL(request.url);
  // Owner-private, read-only bootstrap diagnostic. Disable before enabling controls.
  if(env.IDENTITY_PROBE_ENABLED==="true" && env.REMOTE_CONTROL_ENABLED!=="true" && request.method==="GET" && ["/","/favicon.ico"].includes(url.pathname)) {
    if(!request.headers.get("oai-authenticated-user-id") && !request.headers.get("oai-authenticated-user-email"))throw new Failure(401,"site_sign_in_required");
    if(url.pathname==="/favicon.ico")return new Response(null,{status:204});
    return new Response("<!doctype html><html lang=\"en\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Scheduler diagnostic</title><main><h1>Scheduler Site diagnostic</h1><p>Private sign-in reached the Site. Remote controls and the local bridge are disabled.</p><p><a href=\"/setup/identity\">Inspect supplied identity</a></p></main></html>",{headers:{"Content-Type":"text/html; charset=utf-8"}});
  }
  if(url.pathname==="/setup/identity" && request.method==="GET" && env.IDENTITY_PROBE_ENABLED==="true" && env.REMOTE_CONTROL_ENABLED!=="true") {
    const id=request.headers.get("oai-authenticated-user-id");
    const email=request.headers.get("oai-authenticated-user-email");
    if(!id && !email)throw new Failure(401,"site_sign_in_required");
    return json({site_user_id:id,site_user_email:email});
  }
  const {local}=config(env,url);const db=env.SCHEDULER_REMOTE;const now=clock();
  if(!["GET","POST"].includes(request.method))throw new Failure(405,"method_not_allowed");
  if(request.method==="POST" && !url.pathname.startsWith("/agent/") && request.headers.get("origin")!==url.origin)throw new Failure(403,"same_origin_required");
  if(url.pathname.startsWith("/agent/")) {
    if(request.method!=="POST")throw new Failure(405,"method_not_allowed");
    await agent(request,env);await rate(env,"agent",180,60);
    const body=await objectBody(request,262144);
    if(url.pathname==="/agent/poll") {
      const snapshot=projectSnapshot(body.snapshot);
      const serialized=JSON.stringify(snapshot);
      await db.prepare("INSERT INTO snapshots VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value,source_updated_at=excluded.source_updated_at,received=excluded.received,input_sha256=excluded.input_sha256").bind(serialized,snapshot.updated_at,now,await sha(serialized)).run();
      await db.prepare("UPDATE commands SET state=CASE WHEN state='leased' THEN 'uncertain' ELSE 'expired' END,finished=? WHERE state IN ('queued','leased') AND expires<=?").bind(now,now).run();
      const claimed=await db.prepare("UPDATE commands SET state='leased',lease_until=?,fence=fence+1 WHERE id=(SELECT id FROM commands WHERE expires>? AND (state='queued' OR (state='leased' AND lease_until<?)) ORDER BY created,id LIMIT 1) RETURNING id,payload,fence,expires").bind(now+30,now,now).first();
      if(claimed)await audit(env,"agent","command.claimed",claimed.id,{fence:claimed.fence});
      return json({command:claimed?{...claimed,payload:JSON.parse(claimed.payload)}:null,received_at:new Date(now*1000).toISOString()});
    }
    if(url.pathname==="/agent/ack") {
      if(typeof body.id!=="string" || !Number.isInteger(body.fence) || !["succeeded","failed","rejected","uncertain"].includes(body.status))throw new Failure(422,"invalid_ack");
      const result=JSON.stringify({status:body.status,http_status:Number.isInteger(body.http_status)?body.http_status:null});
      const changed=await db.prepare("UPDATE commands SET state=?,result=?,finished=? WHERE id=? AND fence=? AND state='leased' AND expires>? RETURNING id").bind(body.status,result,now,body.id,body.fence,now).first();
      if(!changed)throw new Failure(409,"stale_ack");
      await audit(env,"agent","command."+body.status,body.id,{fence:body.fence});return json({ok:true});
    }
    throw new Failure(404,"not_found");
  }
  if(url.pathname==="/auth/verify" && request.method==="POST") {
    try{return await login(request,env,local);}catch(error){await audit(env,"anonymous","auth.denied");throw error;}
  }
  if(url.pathname.startsWith("/api/") || url.pathname==="/auth/logout") {
    const auth=await session(request,env);await rate(env,"session:"+auth.hash,180,60);
    if(request.method==="POST" && request.headers.get("x-csrf-token")!==auth.csrf)throw new Failure(403,"csrf_required");
    if(url.pathname==="/auth/logout" && request.method==="POST") {
      await db.prepare("DELETE FROM sessions WHERE hash=?").bind(auth.hash).run();await audit(env,auth.owner,"auth.logout");
      return json({ok:true},200,{"Set-Cookie":"scheduler_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0"});
    }
    if(url.pathname==="/api/session" && request.method==="GET")return json({role:auth.role,csrf:auth.csrf,expires_at:new Date(auth.expires*1000).toISOString()});
    if(url.pathname==="/api/snapshot" && request.method==="GET") {
      const latest=await db.prepare("SELECT * FROM snapshots WHERE id=1").first();
      return json({snapshot:latest?JSON.parse(latest.value):null,received_at:latest?new Date(latest.received*1000).toISOString():null,agent_online:!!latest&&now-latest.received<=30,role:auth.role});
    }
    if(url.pathname==="/api/control" && request.method==="POST") {
      if(auth.role!=="controller" || env.REMOTE_CONTROL_ENABLED!=="true")throw new Failure(403,"read_only");
      const payload=command(await objectBody(request));
      const key=request.headers.get("idempotency-key");if(!key || !/^[A-Za-z0-9_-]{16,128}$/.test(key))throw new Failure(400,"idempotency_key_required");
      const hash=await sha(JSON.stringify(payload));
      const previous=await db.prepare("SELECT id,hash,state FROM commands WHERE id=?").bind(key).first();
      if(previous){if(previous.hash!==hash)throw new Failure(409,"idempotency_conflict");return json(previous,202);}
      const latest=await db.prepare("SELECT received FROM snapshots WHERE id=1").first();
      if(!latest || now-latest.received>30)throw new Failure(503,"agent_offline");
      await db.batch([
        db.prepare("INSERT INTO commands(id,hash,payload,owner,created,expires,state) VALUES(?,?,?,?,?,?,'queued') ON CONFLICT(id) DO NOTHING").bind(key,hash,JSON.stringify(payload),auth.owner,now,now+60),
        db.prepare("INSERT INTO audit(at,actor,kind,command_id,detail) VALUES(?,?,?,?,?)").bind(now,auth.owner,"command.requested",key,JSON.stringify(payload))
      ]);
      const saved=await db.prepare("SELECT id,hash,state FROM commands WHERE id=?").bind(key).first();
      if(saved.hash!==hash)throw new Failure(409,"idempotency_conflict");
      return json(saved,202);
    }
    if(url.pathname==="/api/commands" && request.method==="GET")return json({items:(await db.prepare("SELECT id,payload,state,created,expires,result FROM commands WHERE owner=? ORDER BY created DESC LIMIT 50").bind(auth.owner).all()).results});
    throw new Failure(404,"not_found");
  }
  if(request.method==="GET" && ["/","/index.html","/app.js","/style.css"].includes(url.pathname)) {
    owner(request,env);
    const content=url.pathname==="/app.js"?script:url.pathname==="/style.css"?styles:page;
    const mime=url.pathname==="/app.js"?"text/javascript":url.pathname==="/style.css"?"text/css":"text/html";
    return new Response(content,{headers:{"Content-Type":mime+"; charset=utf-8"}});
  }
  throw new Failure(404,"not_found");
}
export default {
  async fetch(request,env) {
    let response;
    try{response=await route(request,env);}catch(error){response=json({error:error instanceof Failure?error.message:"service_unavailable"},error instanceof Failure?error.status:503);}
    const secured=new Response(response.body,response);const h=secured.headers;
    h.set("Cache-Control","no-store");h.set("X-Content-Type-Options","nosniff");h.set("Referrer-Policy","no-referrer");h.set("X-Frame-Options","DENY");
    h.set("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'");
    return secured;
  }
};
