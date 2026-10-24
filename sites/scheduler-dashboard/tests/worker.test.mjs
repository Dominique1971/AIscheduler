// Direct Worker/SQLite diagnostics with simulated Sites identity; not hosted sign-in acceptance.
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "../dist/server/index.js";

const owner="site-user-fixture-owner", secret="JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP";
function setup() {
  const db=new DatabaseSync(":memory:");db.exec(readFileSync(new URL("../drizzle/0000_scheduler.sql",import.meta.url),"utf8"));
  function stmt(sql,args=[]){return {bind(...a){return stmt(sql,a);},async first(){return db.prepare(sql).get(...args)??null;},async run(){return {meta:{changes:db.prepare(sql).run(...args).changes}};},async all(){return {results:db.prepare(sql).all(...args)};}};}
  const env={APP_ORIGIN:"https://scheduler.test",OWNER_SITE_USER_ID:owner,OWNER_TOTP_SECRET:secret,AGENT_TOKEN:"a".repeat(64),REMOTE_CONTROL_ENABLED:"false",SCHEDULER_REMOTE:{prepare:stmt,async batch(items){db.exec("BEGIN");try{const out=[];for(const item of items)out.push(await item.run());db.exec("COMMIT");return out;}catch(error){db.exec("ROLLBACK");throw error;}}}};
  const call=(path,{body,identity=owner,email,cookie,csrf,agent=false,method}={})=>worker.fetch(new Request(env.APP_ORIGIN+path,{method:method??(body===undefined?"GET":"POST"),headers:{Origin:env.APP_ORIGIN,...(identity?{"oai-authenticated-user-id":identity}:{}),...(email?{"oai-authenticated-user-email":email}:{}),...(cookie?{Cookie:cookie}:{}),...(csrf?{"X-CSRF-Token":csrf}:{}),...(agent?{Authorization:"Bearer "+env.AGENT_TOKEN}:{})},body:body===undefined?undefined:JSON.stringify(body)}),env);
  return {db,env,call};
}
async function code() {
  const alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";let bits=0,buffer=0;const bytes=[];
  for(const c of secret){buffer=(buffer<<5)|alphabet.indexOf(c);bits+=5;if(bits>=8){bits-=8;bytes.push((buffer>>bits)&255);}}
  const key=await crypto.subtle.importKey("raw",Uint8Array.from(bytes),{name:"HMAC",hash:"SHA-1"},false,["sign"]);
  let count=BigInt(Math.floor(Date.now()/30000));const message=new Uint8Array(8);for(let i=7;i>=0;i--){message[i]=Number(count&255n);count>>=8n;}
  const mac=new Uint8Array(await crypto.subtle.sign("HMAC",key,message)),o=mac[19]&15;
  return String(((((mac[o]&127)<<24)|(mac[o+1]<<16)|(mac[o+2]<<8)|mac[o+3])%1000000)).padStart(6,"0");
}
test("anonymous and wrong-owner visitor cannot access page or API",async()=>{const {call,db}=setup();try{for(const identity of [null,"other-user"]){for(const path of ["/","/api/session"]){const r=await call(path,{identity});assert.equal(r.status,403);}}}finally{db.close();}});
test("identity probe is read-only and requires an explicit setup flag",async()=>{const {call,db,env}=setup();try{assert.equal((await call("/setup/identity")).status,404);env.IDENTITY_PROBE_ENABLED="true";assert.equal((await call("/",{identity:null})).status,401);assert.equal((await call("/")).status,200);assert.equal((await call("/setup/identity",{identity:null})).status,401);assert.deepEqual(await (await call("/setup/identity")).json(),{site_user_id:owner,site_user_email:null});env.REMOTE_CONTROL_ENABLED="true";assert.equal((await call("/setup/identity")).status,404);}finally{db.close();}});
test("exact authenticated owner email works when Sites omits a user ID",async()=>{const {call,db,env}=setup();try{delete env.OWNER_SITE_USER_ID;env.OWNER_SITE_EMAIL="owner@example.invalid";assert.equal((await call("/",{identity:null,email:"owner@example.invalid"})).status,200);assert.equal((await call("/",{identity:null,email:"other@example.invalid"})).status,403);}finally{db.close();}});
test("temporary TOTP enrollment is owner-only and closes after first verification",async()=>{const {call,db,env}=setup();try{assert.equal((await call("/setup/totp")).status,404);env.TOTP_ENROLLMENT_ENABLED="true";assert.equal((await call("/setup/totp",{identity:null})).status,403);assert.equal((await call("/setup/totp",{identity:"other-user"})).status,403);const first=await call("/setup/totp");assert.equal(first.status,200);const page=await first.text();assert.match(page,/Manual setup key/);assert.match(page,/Enter a setup key/);assert.equal((await call("/auth/verify",{body:{code:await code()}})).status,200);assert.equal((await call("/setup/totp")).status,404);env.REMOTE_CONTROL_ENABLED="true";assert.equal((await call("/setup/totp")).status,404);}finally{db.close();}});
test("owner must provide separate TOTP; replay and missing CSRF are denied",async()=>{const {call,db}=setup();try{assert.equal((await call("/api/session")).status,401);assert.equal((await call("/auth/verify",{body:{code:"000000"}})).status,401);const one=await call("/auth/verify",{body:{code:await code()}});assert.equal(one.status,200);const cookie=one.headers.get("set-cookie").split(";")[0];assert.match(one.headers.get("set-cookie"),/HttpOnly; Secure; SameSite=Strict/);assert.equal((await call("/auth/verify",{body:{code:await code()}})).status,401);const auth=await (await call("/api/session",{cookie})).json();assert.equal(auth.role,"reader");assert.equal((await call("/auth/logout",{body:{},cookie})).status,403);assert.equal((await call("/auth/logout",{body:{},cookie,csrf:auth.csrf})).status,200);assert.equal((await call("/api/session",{cookie})).status,401);}finally{db.close();}});
test("bridge agent requires a distinct credential",async()=>{const {call,db}=setup();try{assert.equal((await call("/agent/poll",{body:{}})).status,401);assert.equal((await call("/agent/poll",{body:{},agent:true})).status,422);}finally{db.close();}});
