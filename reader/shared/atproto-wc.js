class W extends HTMLElement{root;_rendered=!1;_abort=null;constructor(){super();xn(),this.root=this.attachShadow({mode:"open"})}connectedCallback(){if(typeof customElements>"u")return;if(!this._rendered)this._rendered=!0,this.onConnect()}disconnectedCallback(){this._abort?.abort(),this._abort=null}attributeChangedCallback(r,f,n){if(this._rendered)this.onAttributeChange(r)}onConnect(){this._refresh()}onAttributeChange(r){this._refresh()}async _refresh(){this._abort?.abort(),this._abort=new AbortController;let r=this._abort.signal;try{await this.refresh({signal:r})}catch(f){if(_n(f))return;let n=f instanceof Error?f.message:String(f);this.paintError(n,this.errorCss(),this.classifyError(f))}}errorCss(){return h}paint(r,f){this.root.innerHTML=`<style>${f}</style>${r}`}paintLoading(r){this.root.innerHTML=`<style>${r}</style>${this.loadingSkeleton()}`}loadingSkeleton(){return`<div part="loading" class="loading" role="status" aria-busy="true">
      <span class="sr-only">Loading…</span>
      <div part="skeleton-bar" class="skeleton-bar"></div>
      <div part="skeleton-bar" class="skeleton-bar short"></div>
    </div>`}paintError(r,f,n="transient"){let v=jn(r),$=n==="transient"?'<button type="button" part="retry" class="retry" data-action="retry">Retry</button>':"";this.root.innerHTML=`<style>${f}</style>
      <div part="error" class="error" role="alert">
        <span part="error-label" class="error-label">${Bn(n)}</span>
        <span part="error-message" class="error-message">${v}</span>
        ${$}
      </div>`,this.root.querySelector("button.retry")?.addEventListener("click",()=>void this._refresh())}classifyError(r){let f=r instanceof Error?r.message:String(r);if(/not an at-uri|invalid did|invalid handle|unrecognized post source|missing `src`/i.test(f))return"permanent";if(/404|not found|no PDS service entry/i.test(f))return"not-found";return"transient"}}function Bn(r){switch(r){case"not-found":return"Not found";case"permanent":return"Input error";case"transient":return"Connection issue"}}function _n(r){return r instanceof DOMException&&r.name==="AbortError"||r instanceof Error&&r.name==="AbortError"}function jn(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}var Mn=`
:root {
  /* Colors — base palette */
  --atproto-bg: #ffffff;
  --atproto-text: #0b0f15;
  --atproto-muted: #5d6c7f;
  --atproto-accent: #1185fe;
  --atproto-border: #e1e5eb;
  --atproto-error: #d7263d;
  --atproto-warning: #d97706;
  --atproto-success: #16a34a;
  --atproto-subtle: color-mix(in srgb, var(--atproto-border) 25%, transparent);

  /* Colors — interactive states. Override to re-skin hovers, tints, focus
     rings without touching individual components. */
  --atproto-accent-soft: color-mix(in srgb, var(--atproto-accent) 12%, transparent);
  --atproto-accent-hover: color-mix(in srgb, var(--atproto-accent) 85%, var(--atproto-text));
  --atproto-hover-bg: var(--atproto-subtle);
  --atproto-focus-ring: var(--atproto-accent);
  --atproto-link: var(--atproto-accent);
  --atproto-link-visited: var(--atproto-accent);

  /* Typography */
  --atproto-font: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --atproto-font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --atproto-font-size-xs: 0.75rem;
  --atproto-font-size-sm: 0.85rem;
  --atproto-font-size: 0.95rem;
  --atproto-font-size-lg: 1.15rem;
  --atproto-font-size-xl: 1.5rem;
  --atproto-line-height: 1.5;
  --atproto-line-height-tight: 1.25;
  --atproto-letter-spacing-tight: -0.01em;
  --atproto-font-weight: 400;
  --atproto-font-weight-semibold: 600;
  --atproto-font-weight-bold: 700;

  /* Spacing scale */
  --atproto-space-1: 0.25rem;
  --atproto-space-2: 0.5rem;
  --atproto-space-3: 0.75rem;
  --atproto-space-4: 1rem;
  --atproto-space-5: 1.25rem;
  --atproto-space-6: 1.5rem;

  /* Radii */
  --atproto-radius-sm: 4px;
  --atproto-radius-inner: 8px;
  --atproto-radius: 12px;
  --atproto-radius-lg: 16px;
  --atproto-radius-pill: 999px;

  /* Sizes */
  --atproto-avatar-size: 40px;
  --atproto-avatar-size-sm: 24px;
  --atproto-avatar-size-lg: 80px;
  --atproto-max-width: 560px;

  /* Elevation — off by default (flat borders), opt-in via override. */
  --atproto-shadow-sm: 0 1px 2px -1px color-mix(in srgb, var(--atproto-text) 10%, transparent);
  --atproto-shadow-md: 0 4px 12px -4px color-mix(in srgb, var(--atproto-text) 15%, transparent);
  --atproto-shadow-lg: 0 10px 40px -20px color-mix(in srgb, var(--atproto-text) 25%, transparent);
  --atproto-shadow: none;

  /* Motion — single duration + easing controls every hover/focus transition. */
  --atproto-transition-duration: 0.15s;
  --atproto-transition-easing: ease;
  --atproto-transition: color var(--atproto-transition-duration) var(--atproto-transition-easing),
                        background var(--atproto-transition-duration) var(--atproto-transition-easing),
                        border-color var(--atproto-transition-duration) var(--atproto-transition-easing),
                        box-shadow var(--atproto-transition-duration) var(--atproto-transition-easing),
                        transform var(--atproto-transition-duration) var(--atproto-transition-easing);
}
@media (prefers-color-scheme: dark) {
  :root {
    --atproto-bg: #0b0f15;
    --atproto-text: #e8ecf2;
    --atproto-muted: #8b98a8;
    --atproto-border: #1e2936;
    --atproto-error: #ff6478;
    --atproto-warning: #fbbf24;
    --atproto-success: #4ade80;
  }
}
`,Vr=!1;function xn(){if(Vr)return;if(typeof document>"u")return;if(document.getElementById("atproto-wc-defaults")){Vr=!0;return}let r=document.createElement("style");r.id="atproto-wc-defaults",r.textContent=Mn,document.head.prepend(r),Vr=!0}var h=`
:host {
  color: var(--atproto-text);
  background: transparent;
  font-family: var(--atproto-font);
  font-size: var(--atproto-font-size);
  line-height: var(--atproto-line-height);
  display: block;
  /* Default to filling the available width; the inner article caps at
     max-width: var(--atproto-max-width). Without this, custom-element hosts
     placed in flex/grid contexts shrink to their content min-width and the
     author row collapses to a single-character vertical column. */
  width: 100%;
  box-sizing: border-box;
}
*, *::before, *::after { box-sizing: border-box; }

.sr-only {
  position: absolute;
  width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

/* Loading skeleton */
.loading {
  padding: var(--atproto-space-3);
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-2);
  max-width: var(--atproto-max-width);
}
.skeleton-bar {
  height: 0.85rem;
  background: linear-gradient(90deg, var(--atproto-border) 0%, var(--atproto-subtle) 50%, var(--atproto-border) 100%);
  background-size: 200% 100%;
  animation: atproto-shimmer 1.5s infinite linear;
  border-radius: var(--atproto-radius-sm);
}
.skeleton-bar.short { width: 60%; }
.skeleton-block {
  background: linear-gradient(90deg, var(--atproto-border) 0%, var(--atproto-subtle) 50%, var(--atproto-border) 100%);
  background-size: 200% 100%;
  animation: atproto-shimmer 1.5s infinite linear;
  border-radius: var(--atproto-radius-sm);
}
.skeleton-circle {
  background: linear-gradient(90deg, var(--atproto-border) 0%, var(--atproto-subtle) 50%, var(--atproto-border) 100%);
  background-size: 200% 100%;
  animation: atproto-shimmer 1.5s infinite linear;
  border-radius: 50%;
  flex-shrink: 0;
}
@keyframes atproto-shimmer {
  to { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-bar, .skeleton-block, .skeleton-circle { animation: none; }
}

/* Error state */
.error {
  padding: var(--atproto-space-3);
  background: var(--atproto-bg);
  border: 1px solid color-mix(in srgb, var(--atproto-error) 60%, var(--atproto-border));
  border-radius: var(--atproto-radius);
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-2);
  color: var(--atproto-text);
  font: inherit;
}
.error-label {
  font-size: var(--atproto-font-size-xs);
  font-weight: var(--atproto-font-weight-semibold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--atproto-error);
}
.error-message {
  font-size: var(--atproto-font-size-sm);
  color: var(--atproto-muted);
  word-break: break-word;
}
.retry {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.retry {
  transition: var(--atproto-transition);
}
.retry:hover { background: var(--atproto-hover-bg); border-color: var(--atproto-accent); }

/* Focus visibility — applies to all internal focusables */
a:focus-visible,
button:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid var(--atproto-focus-ring);
  outline-offset: 2px;
  border-radius: var(--atproto-radius-sm);
}

/* Link semantics — override via --atproto-link / --atproto-link-visited */
a { color: var(--atproto-link); }
a:visited { color: var(--atproto-link-visited); }
a:hover { color: var(--atproto-accent-hover); }
`;var In=/^at:\/\/(did:[^/]+)\/([^/]+)\/([^/]+)$/,yn=/^https?:\/\/bsky\.app\/profile\/([^/]+)\/post\/([^/?#]+)/;function x(r){let f=r.match(In);if(!f)throw Error(`not an at-uri: ${r}`);return{did:f[1],collection:f[2],rkey:f[3]}}function J(r){return`at://${r.did}/${r.collection}/${r.rkey}`}function Fr(r){return yn.test(r)}function Gr(r){let f=r.match(yn);if(!f)throw Error(`not a bsky.app post url: ${r}`);return{handleOrDid:f[1],rkey:f[2]}}var g=new Map;async function M(r,f={}){let n=r.toString(),v=f.ttlMs??1e4,$=Date.now();if(!f.bypass){let u=g.get(n);if(u){if(u.data&&u.data.expires>$)return u.data.value;if(u.inflight)return u.inflight}}let y=(async()=>{try{let u=await fetch(n,{signal:f.signal});if(!u.ok)throw new Jr(`${u.status} ${u.statusText}`,u.status,n);let w=await u.json();if(v>0)g.set(n,{data:{value:w,expires:Date.now()+v}});else g.delete(n);return w}catch(u){throw g.delete(n),u}})();return g.set(n,{inflight:y}),y}class Jr extends Error{status;url;constructor(r,f,n){super(`${r} — ${n}`);this.status=f;this.url=n;this.name="CacheFetchError"}}function Rn(){g.clear()}var Hn="https://plc.directory",Tn=/^did:(plc|web):[a-z0-9][a-z0-9._:%-]*$/i;function un(r){if(!Tn.test(r))throw Error(`invalid did: ${r}`)}async function G(r,f={}){if(un(r),r.startsWith("did:plc:"))return await M(`${Hn}/${r}`,{ttlMs:300000,...f.signal?{signal:f.signal}:{}});if(r.startsWith("did:web:")){let n=decodeURIComponent(r.slice(8)).replace(/:/g,"/");return await M(`https://${n}/.well-known/did.json`,{ttlMs:300000,...f.signal?{signal:f.signal}:{}})}throw Error(`unsupported did method: ${r}`)}async function V(r,f={}){let v=(await G(r,f)).service?.find((y)=>y.type==="AtprotoPersonalDataServer"||y.id.endsWith("#atproto_pds"));if(!v?.serviceEndpoint)throw Error(`no PDS service entry on ${r}`);let $=v.serviceEndpoint.replace(/\/$/,"");if(!$.startsWith("https://"))throw Error(`PDS endpoint is not https: ${$}`);return $}var Br=new Map;function Z(r,f={}){if(!/^[a-z0-9][a-z0-9.-]*$/i.test(r))throw Error(`invalid handle: ${r}`);let n=Br.get(r);if(n)return n;let v=(async()=>{let $=await fetch(`https://${r}/.well-known/atproto-did`,{...f.signal?{signal:f.signal}:{}});if(!$.ok)throw Error(`handle ${r} well-known: ${$.status}`);let y=(await $.text()).trim();if(!y.startsWith("did:"))throw Error(`handle ${r} returned non-did: ${y}`);return un(y),y})();return Br.set(r,v),v.catch(()=>Br.delete(r)),v}async function N(r,f,n,v={}){let $=await V(r,v),y=new URL(`${$}/xrpc/com.atproto.repo.getRecord`);return y.searchParams.set("repo",r),y.searchParams.set("collection",f),y.searchParams.set("rkey",n),await M(y,v.signal?{signal:v.signal}:{})}async function H(r,f,n={}){let v=await V(r,n),$=new URL(`${v}/xrpc/com.atproto.repo.listRecords`);if($.searchParams.set("repo",r),$.searchParams.set("collection",f),n.limit!==void 0)$.searchParams.set("limit",String(n.limit));if(n.cursor)$.searchParams.set("cursor",n.cursor);if(n.reverse)$.searchParams.set("reverse","true");return await M($,n.signal?{signal:n.signal}:{})}async function _r(r,f={}){let n=await V(r,f),v=new URL(`${n}/xrpc/com.atproto.repo.describeRepo`);return v.searchParams.set("repo",r),await M(v,f.signal?{signal:f.signal}:{})}async function jr(r,f={}){let n=await V(r,f),v=new URL(`${n}/xrpc/com.atproto.sync.listBlobs`);if(v.searchParams.set("did",r),f.limit!==void 0)v.searchParams.set("limit",String(f.limit));if(f.cursor)v.searchParams.set("cursor",f.cursor);if(f.since)v.searchParams.set("since",f.since);return await M(v,f.signal?{signal:f.signal}:{})}async function Mr(r,f={}){let n=await V(r,f),v=new URL(`${n}/xrpc/com.atproto.sync.getLatestCommit`);return v.searchParams.set("did",r),await M(v,f.signal?{signal:f.signal}:{})}async function o(r,f={}){let n=await V(r,f),v=new URL(`${n}/xrpc/com.atproto.sync.getRepoStatus`);return v.searchParams.set("did",r),await M(v,f.signal?{signal:f.signal}:{})}var gn="234567abcdefghijklmnopqrstuvwxyz";function xr(r){if(r.length!==13)return null;let f=0n;for(let $ of r){let y=gn.indexOf($);if(y<0)return null;f=f<<5n|BigInt(y)}let n=Number(f>>10n),v=Math.floor(n/1000);if(!Number.isFinite(v)||v<=0)return null;return new Date(v)}var An="https://constellation.microcosm.blue",ir=An;function On(r){ir=r.replace(/\/$/,"")}function bn(){return ir}function Ir(r,f){return`${r}:${f.replace(/^\./,"")}`}function A(r){return(r.endpoint??ir).replace(/\/$/,"")}async function Q(r,f,n,v={}){let $=new URL(`${A(v)}/xrpc/blue.microcosm.links.getBacklinksCount`);return $.searchParams.set("subject",r),$.searchParams.set("source",Ir(f,n)),(await M($,v.signal?{signal:v.signal}:{})).total}async function X(r,f,n,v={}){let $=new URL(`${A(v)}/xrpc/blue.microcosm.links.getBacklinks`);if($.searchParams.set("subject",r),$.searchParams.set("source",Ir(f,n)),v.limit!==void 0)$.searchParams.set("limit",String(v.limit));if(v.cursor)$.searchParams.set("cursor",v.cursor);if(v.reverse)$.searchParams.set("reverse","true");return await M($,v.signal?{signal:v.signal}:{})}async function Rr(r,f,n,v={}){let $=new URL(`${A(v)}/links/distinct-dids`);if($.searchParams.set("target",r),$.searchParams.set("collection",f),$.searchParams.set("path",n.startsWith(".")?n:`.${n}`),v.limit!==void 0)$.searchParams.set("limit",String(v.limit));if(v.cursor)$.searchParams.set("cursor",v.cursor);let y=await M($,v.signal?{signal:v.signal}:{});return{total:y.total,dids:y.linking_dids??[],cursor:y.cursor??null}}async function Hr(r,f,n,v={}){let $=new URL(`${A(v)}/links/count/distinct-dids`);return $.searchParams.set("target",r),$.searchParams.set("collection",f),$.searchParams.set("path",n.startsWith(".")?n:`.${n}`),(await M($,v.signal?{signal:v.signal}:{})).total}async function Tr(r,f,n,v,$={}){let y=new URL(`${A($)}/xrpc/blue.microcosm.links.getManyToMany`);if(y.searchParams.set("subject",r),y.searchParams.set("otherSubject",f),y.searchParams.set("source",Ir(n,v)),y.searchParams.set("pathToOther",v.replace(/^\./,"")),$.limit!==void 0)y.searchParams.set("limit",String($.limit));if($.cursor)y.searchParams.set("cursor",$.cursor);let u=await M(y,$.signal?{signal:$.signal}:{}),w=Array.isArray(u.items)?u.items:[],z=w.map((L)=>{if(typeof L==="string"&&L.startsWith("did:"))return L;if(L&&typeof L==="object"&&"did"in L&&typeof L.did==="string")return L.did;return null}).filter((L)=>L!==null);return{total:u.total??w.length,dids:z,cursor:u.cursor??null}}async function gr(r,f={}){let n=new URL(`${A(f)}/links/all`);n.searchParams.set("target",r);let v=await M(n,f.signal?{signal:f.signal}:{}),$={},y=v.links??{};for(let[u,w]of Object.entries(y))for(let[z,L]of Object.entries(w)){let K=`${u}:${z}`;$[K]={collection:u,path:z,records:L.records,distinct_dids:L.distinct_dids}}return $}var m={like:{collection:"app.bsky.feed.like",path:"subject.uri"},repost:{collection:"app.bsky.feed.repost",path:"subject.uri"},reply:{collection:"app.bsky.feed.post",path:"reply.parent.uri"},threadRoot:{collection:"app.bsky.feed.post",path:"reply.root.uri"},quote:{collection:"app.bsky.feed.post",path:"embed.record.uri"},follow:{collection:"app.bsky.graph.follow",path:"subject"},mention:{collection:"app.bsky.feed.post",path:"facets[app.bsky.richtext.facet].features[app.bsky.richtext.facet#mention].did"},citation:{collection:"app.bsky.feed.post",path:"facets[app.bsky.richtext.facet].features[app.bsky.richtext.facet#link].uri"},listMember:{collection:"app.bsky.graph.listitem",path:"subject"},listContains:{collection:"app.bsky.graph.listitem",path:"list"},block:{collection:"app.bsky.graph.block",path:"subject"},verification:{collection:"app.bsky.graph.verification",path:"subject"},pinnedPost:{collection:"app.bsky.actor.profile",path:"pinnedPost.uri"},threadgate:{collection:"app.bsky.feed.threadgate",path:"post"},postgate:{collection:"app.bsky.feed.postgate",path:"post"}};async function B(r,f={}){if(r.startsWith("at://"))return x(r);if(Fr(r)){let{handleOrDid:n,rkey:v}=Gr(r);return{did:n.startsWith("did:")?n:await Z(n,f),collection:"app.bsky.feed.post",rkey:v}}throw Error(`unrecognized post source: ${r}`)}var kn=/^(https?|mailto):/i,an=/[\x00-\x20\x7f]/g;function O(r){if(typeof r!=="string")return"#";let f=r.replace(an,"").trim();if(!f)return"#";if(kn.test(f))return f;if(f.startsWith("//")||f.startsWith("/")||f.startsWith("#"))return f;if(!/^[a-z][a-z0-9+.-]*:/i.test(f))return f;return"#"}async function Ar(r,f){return await Promise.all(r.map(async(v)=>{try{let[$,y,u]=await Promise.all([G(v,{signal:f}),V(v,{signal:f}),N(v,"app.bsky.actor.profile","self",{signal:f}).catch(()=>null)]),w=$.alsoKnownAs?.find((Y)=>Y.startsWith("at://")),z=w?w.slice(5):v,L=u?.value,K=L?.avatar?`${y}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(v)}&cid=${encodeURIComponent(L.avatar.ref.$link)}`:null;return{did:v,handle:z,displayName:L?.displayName??z,avatarUrl:K}}catch{return{did:v,handle:v,displayName:v,avatarUrl:null}}}))}var E=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.wrap {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  padding: var(--atproto-space-3) var(--atproto-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-3);
}
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}
.head:empty { display: none; }
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: var(--atproto-space-2);
  list-style: none;
  padding: 0;
  margin: 0;
}
.actor {
  display: block;
  text-decoration: none;
  color: inherit;
}
.actor-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--atproto-border);
  overflow: hidden;
  aspect-ratio: 1;
}
.actor-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.actor:hover .actor-avatar,
.actor:focus-visible .actor-avatar {
  outline: 2px solid var(--atproto-accent);
  outline-offset: 2px;
}
.actor:focus { outline: none; }
.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--atproto-space-2);
}
.loadmore {
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
.empty {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  padding: var(--atproto-space-2) 0;
  /* When appended as a direct child of .grid (display: grid with auto-fill cols
     of 44-150px), the empty/error message would be constrained to one tiny
     grid cell — making each word wrap to its own line. Span all columns. */
  grid-column: 1 / -1;
  word-break: normal;
  overflow-wrap: anywhere;
}
`;function l(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Or(r){let f=`https://bsky.app/profile/${encodeURIComponent(r.handle)}`,n=r.avatarUrl?`<img src="${l(r.avatarUrl)}" alt="">`:"";return`<a part="actor" class="actor" href="${l(f)}" rel="noopener noreferrer" target="_blank" title="${l(r.displayName)} (@${l(r.handle)})">
    <div part="actor-avatar" class="actor-avatar" aria-hidden="true">${n}</div>
  </a>`}class i extends W{#r;#f=!1;#n=null;errorCss(){return E}headLabel(r){return r===void 0?"":`<b>${r.toLocaleString()}</b> actors`}loadingSkeleton(){return`<section part="loading" class="wrap" aria-busy="true" role="status">
      <span class="sr-only">Loading…</span>
      <ul class="grid">${'<li><div class="actor-avatar skeleton-circle" style="width:44px;height:44px"></div></li>'.repeat(8)}</ul>
    </section>`}async refresh(r){this.#r=void 0,this.#f=!1,this.#n=r.signal,this.paintLoading(E),this.root.innerHTML=`<style>${E}</style>
      <section class="wrap">
        <header part="head" class="head" aria-live="polite"></header>
        <ul part="grid" class="grid"></ul>
        <footer class="footer">
          <button part="loadmore" class="loadmore" type="button">Load more</button>
        </footer>
      </section>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#v()),await this.#v()}async#v(){if(!this.#n||this.#f)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".grid"),n=this.root.querySelector(".head");if(!f||!r)return;r.disabled=!0,r.textContent="Loading…";try{let v=await this.fetchPage({signal:this.#n,cursor:this.#r});if(n&&v.total!==void 0)n.innerHTML=this.headLabel(v.total);if(v.dids.length>0){let $=await Ar(v.dids,this.#n);for(let y of $){let u=document.createElement("li");u.innerHTML=Or(y),f.appendChild(u)}}if(this.#r=v.cursor??void 0,this.#f=!v.cursor||v.dids.length===0,f.children.length===0)f.innerHTML='<div part="empty" class="empty">no one yet</div>';if(r.disabled=this.#f,r.textContent=this.#f?"End":"Load more",this.#f)r.hidden=!0}catch(v){r.disabled=!1,r.textContent="Retry";let $=document.createElement("div");$.className="empty",$.setAttribute("part","empty"),$.textContent=`error: ${v instanceof Error?v.message:String(v)}`,f.appendChild($)}}}var C=`
${h}
:host { display: inline; width: auto; }
time { color: inherit; }
`;class br extends W{static observedAttributes=["datetime"];errorCss(){return C}refresh(r){let f=this.getAttribute("datetime");if(!f){this.paintError("missing `datetime` attribute (ISO 8601)",C,"permanent");return}let n=new Date(f).getTime();if(Number.isNaN(n)){this.paintError(`invalid datetime: ${f}`,C,"permanent");return}this.paint(`<time part="time" datetime="${wn(f)}">${wn(zn(n))}</time>`,C)}}function wn(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function zn(r){let f=Math.max(0,Date.now()-r),n=Math.floor(f/1000);if(n<60)return`${n}s`;let v=Math.floor(n/60);if(v<60)return`${v}m`;let $=Math.floor(v/60);if($<24)return`${$}h`;let y=Math.floor($/24);if(y<7)return`${y}d`;return new Date(r).toLocaleDateString()}function kr(r="atproto-time"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,br)}function b(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function S(r,f){if(!f?.length)return b(r);let n=new TextEncoder,v=new TextDecoder,$=n.encode(r),y=[...f].sort((z,L)=>z.index.byteStart-L.index.byteStart),u=0,w="";for(let z of y){if(z.index.byteStart<u)continue;w+=b(v.decode($.slice(u,z.index.byteStart)));let L=b(v.decode($.slice(z.index.byteStart,z.index.byteEnd))),K=z.features[0];if(K&&"$type"in K)if(K.$type==="app.bsky.richtext.facet#link")w+=`<a href="${b(O(K.uri))}" rel="noopener noreferrer" target="_blank">${L}</a>`;else if(K.$type==="app.bsky.richtext.facet#tag")w+=`<span class="tag">${L}</span>`;else if(K.$type==="app.bsky.richtext.facet#mention")w+=`<span class="mention" data-did="${b(K.did)}">${L}</span>`;else w+=L;else w+=L;u=z.index.byteEnd}return w+=b(v.decode($.slice(u))),w}var mn=`
${h}
:host { display: block; }
.text {
  white-space: pre-wrap;
  word-wrap: break-word;
}
.text a { color: var(--atproto-accent); text-decoration: none; }
.text a:hover { text-decoration: underline; }
.text .tag, .text .mention { color: var(--atproto-accent); }
`;class ar extends W{static observedAttributes=["text","facets"];#r=null;set facets(r){this.#r=r??null,this.refresh({signal:new AbortController().signal})}get facets(){return this.#r}errorCss(){return mn}refresh(r){let f=this.getAttribute("text")??"",n;if(this.#r)n=this.#r;else{let $=this.getAttribute("facets");if($)try{let y=JSON.parse($);if(Array.isArray(y))n=y}catch{}}let v=S(f,n);this.paint(`<div part="text" class="text">${v}</div>`,mn)}}function or(r="atproto-rich-text"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,ar)}var D=`
${h}
:host {
  display: inline-block;
  width: auto;
}
.avatar {
  display: inline-block;
  width: var(--atproto-avatar-size);
  height: var(--atproto-avatar-size);
  border-radius: 50%;
  background: var(--atproto-border);
  overflow: hidden;
  vertical-align: middle;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
a.avatar-link { display: inline-block; line-height: 0; text-decoration: none; }
a.avatar-link:hover .avatar { outline: 2px solid var(--atproto-accent); outline-offset: 2px; }
:host([size="sm"]) .avatar { width: var(--atproto-avatar-size-sm); height: var(--atproto-avatar-size-sm); }
:host([size="lg"]) .avatar { width: var(--atproto-avatar-size-lg); height: var(--atproto-avatar-size-lg); }
`;class Er extends W{static observedAttributes=["src","size","linked"];errorCss(){return D}loadingSkeleton(){return'<div part="avatar" class="avatar skeleton-circle" aria-busy="true" role="img" aria-label="Loading avatar"></div>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle, did, or at-uri)",D,"permanent");return}this.paintLoading(D);let n=await on(f,r.signal),[v,$,y]=await Promise.all([N(n,"app.bsky.actor.profile","self",{signal:r.signal}).catch(()=>null),En(n,r.signal),V(n,{signal:r.signal})]),u=v?.value.avatar,w=u?`${y}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(n)}&cid=${encodeURIComponent(u.ref.$link)}`:"",z=v?.value.displayName??$,L=this.hasAttribute("linked"),K=w?`<div part="avatar" class="avatar"><img src="${d(w)}" alt="${d(z)}"></div>`:`<div part="avatar" class="avatar" aria-label="${d(z)}"></div>`;if(L){let Y=`https://bsky.app/profile/${encodeURIComponent($)}`;this.paint(`<a part="link" class="avatar-link" href="${d(Y)}" rel="noopener noreferrer" target="_blank">${K}</a>`,D)}else this.paint(K,D)}}async function on(r,f){if(r.startsWith("did:"))return r;if(r.startsWith("at://")){let n=r.slice(5).split("/")[0];if(!n)throw Error(`invalid at-uri: ${r}`);return n.startsWith("did:")?n:await Z(n,{signal:f})}return await Z(r,{signal:f})}async function En(r,f){let v=(await G(r,{signal:f})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function d(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Dr(r="atproto-avatar"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Er)}var s=`
${h}
:host { display: inline; width: auto; color: var(--atproto-muted); }
.handle { color: inherit; text-decoration: none; }
.handle:hover { text-decoration: underline; }
`;class Ur extends W{static observedAttributes=["src","linked","bare"];errorCss(){return s}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle, did, or at-uri)",s,"permanent");return}let n=await Dn(f,r.signal),v=await tn(n,r.signal),$=this.hasAttribute("bare")?v:`@${v}`;if(this.hasAttribute("linked")){let u=`https://bsky.app/profile/${encodeURIComponent(v)}`;this.paint(`<a part="handle" class="handle" href="${tr(u)}" rel="noopener noreferrer" target="_blank">${tr($)}</a>`,s)}else this.paint(`<span part="handle" class="handle">${tr($)}</span>`,s)}}async function Dn(r,f){if(r.startsWith("did:"))return r;if(r.startsWith("at://")){let n=r.slice(5).split("/")[0];if(!n)throw Error(`invalid at-uri: ${r}`);return n.startsWith("did:")?n:await Z(n,{signal:f})}return await Z(r,{signal:f})}async function tn(r,f){let v=(await G(r,{signal:f})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function tr(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function pr(r="atproto-handle"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Ur)}var c=`
${h}
:host { display: inline; width: auto; font-weight: var(--atproto-font-weight-semibold); }
.name { color: inherit; text-decoration: none; }
:host([linked]) .name:hover { text-decoration: underline; }
`;class Cr extends W{static observedAttributes=["src","linked"];errorCss(){return c}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle, did, or at-uri)",c,"permanent");return}let n=await Un(f,r.signal),[v,$]=await Promise.all([N(n,"app.bsky.actor.profile","self",{signal:r.signal}).catch(()=>null),pn(n,r.signal)]),y=v?.value.displayName?.trim()||$;if(this.hasAttribute("linked")){let w=`https://bsky.app/profile/${encodeURIComponent($)}`;this.paint(`<a part="name" class="name" href="${lr(w)}" rel="noopener noreferrer" target="_blank">${lr(y)}</a>`,c)}else this.paint(`<span part="name" class="name">${lr(y)}</span>`,c)}}async function Un(r,f){if(r.startsWith("did:"))return r;if(r.startsWith("at://")){let n=r.slice(5).split("/")[0];if(!n)throw Error(`invalid at-uri: ${r}`);return n.startsWith("did:")?n:await Z(n,{signal:f})}return await Z(r,{signal:f})}async function pn(r,f){let v=(await G(r,{signal:f})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function lr(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Sr(r="atproto-display-name"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Cr)}var dr=`
${h}
:host { display: block; }
.row {
  display: flex;
  gap: clamp(var(--atproto-space-3), 3vw, var(--atproto-space-5));
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  flex-wrap: wrap;
}
.row b {
  color: var(--atproto-text);
  font-weight: var(--atproto-font-weight-semibold);
  margin-right: var(--atproto-space-1);
  font-variant-numeric: tabular-nums;
}
`;class sr extends W{static observedAttributes=["src","show","constellation"];errorCss(){return dr}loadingSkeleton(){return`<div part="row" class="row" role="status" aria-busy="true">
      <span class="sr-only">Loading engagement counts…</span>
      <span><span class="skeleton-bar" style="display:inline-block;width:3ch;height:0.85em"></span> replies</span>
      <span><span class="skeleton-bar" style="display:inline-block;width:3ch;height:0.85em"></span> reposts</span>
      <span><span class="skeleton-bar" style="display:inline-block;width:3ch;height:0.85em"></span> likes</span>
    </div>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri or bsky.app url)",dr,"permanent");return}let n=(this.getAttribute("show")??"replies,reposts,quotes,likes").split(",").map((j)=>j.trim().toLowerCase()).filter(Boolean),v=this.getAttribute("constellation")??void 0,$=await B(f,{signal:r.signal}),y=J($),u={signal:r.signal,...v?{endpoint:v}:{}},w=(j)=>n.includes(j),[z,L,K,Y]=await Promise.all([w("likes")?Q(y,m.like.collection,m.like.path,u).catch(()=>0):0,w("reposts")?Q(y,m.repost.collection,m.repost.path,u).catch(()=>0):0,w("replies")?Q(y,m.reply.collection,m.reply.path,u).catch(()=>0):0,w("quotes")?Q(y,m.quote.collection,m.quote.path,u).catch(()=>0):0]),P={replies:K,reposts:L,quotes:Y,likes:z},_=n.filter((j)=>(j in P)).map((j)=>`<span part="count"><b>${P[j].toLocaleString()}</b> ${ln(j)}</span>`).join("");this.paint(`<div part="row" class="row">${_}</div>`,dr)}}function ln(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function cr(r="atproto-engagement-row"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,sr)}var e=`
${h}
:host { display: inline-block; width: auto; }
.count {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35ch;
  font-variant-numeric: tabular-nums;
  color: var(--atproto-accent);
  font-weight: var(--atproto-font-weight-semibold);
}
.count .label {
  color: var(--atproto-muted);
  font-weight: var(--atproto-font-weight);
}
`;class er extends W{static observedAttributes=["src","constellation"];errorCss(){return e}loadingSkeleton(){return'<span part="loading" class="count" aria-busy="true"><span class="sr-only">Loading…</span><span style="display:inline-block;width:2ch;height:0.9em;background:var(--atproto-border);border-radius:var(--atproto-radius-sm)"></span></span>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (at-uri or bsky.app post url)",e,"permanent");return}this.paintLoading(e);let n=this.getAttribute("constellation")??void 0,v=await B(f,{signal:r.signal}),$=await Q(J(v),m.like.collection,m.like.path,{signal:r.signal,...n?{endpoint:n}:{}}),y=$===1?"like":"likes";this.paint(`<span part="count" class="count"><span part="number">${$.toLocaleString()}</span><span part="label" class="label">${y}</span></span>`,e)}}function rf(r="atproto-like-count"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,er)}var rr=`
${h}
/* Container query needs to live on :host (or a parent of article) — a query
   targeting article doesn't fire if article is itself the container. */
:host { container-type: inline-size; }

article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  padding: var(--atproto-space-4);
  box-shadow: var(--atproto-shadow);
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: var(--atproto-space-3);
  row-gap: var(--atproto-space-2);
  max-width: var(--atproto-max-width);
  transition: var(--atproto-transition);
}
:host([compact]) article {
  padding: var(--atproto-space-3);
  column-gap: var(--atproto-space-2);
  row-gap: var(--atproto-space-1);
  font-size: var(--atproto-font-size-sm);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-subtle);
}
.avatar-link {
  grid-row: 1 / span 3;
  display: block;
  border-radius: 50%;
  text-decoration: none;
  color: inherit;
}
.avatar {
  width: var(--atproto-avatar-size);
  height: var(--atproto-avatar-size);
  border-radius: 50%;
  background: var(--atproto-border);
  overflow: hidden;
}
:host([compact]) .avatar { width: var(--atproto-avatar-size-sm); height: var(--atproto-avatar-size-sm); }
:host([compact]) .avatar-link { grid-row: 1 / span 2; }
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }

.author {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--atproto-space-1);
  min-width: 0;
}
.author a {
  color: inherit;
  text-decoration: none;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--atproto-space-1);
  min-width: 0;
}
.author a:hover .display-name,
.author a:hover .handle,
.author a:hover .time {
  text-decoration: underline;
}
.display-name {
  font-weight: var(--atproto-font-weight-semibold);
  letter-spacing: var(--atproto-letter-spacing-tight);
  overflow-wrap: anywhere;
  word-break: normal;
  min-width: 0;
}
.handle, .time {
  color: var(--atproto-muted);
  font-size: 0.9em;
  overflow-wrap: anywhere;
  min-width: 0;
}
.time::before { content: "·"; margin-right: var(--atproto-space-1); }

.body { grid-column: 2; display: flex; flex-direction: column; gap: var(--atproto-space-1); min-width: 0; }

.text { white-space: pre-wrap; word-wrap: break-word; }
.text a { color: var(--atproto-accent); text-decoration: none; }
.text a:hover { text-decoration: underline; }
.text .tag, .text .mention { color: var(--atproto-accent); }

.images {
  display: grid;
  gap: 4px;
  border-radius: var(--atproto-radius-inner);
  overflow: hidden;
  margin-top: var(--atproto-space-2);
}
.images.n-1 img {
  max-height: 520px;
  width: 100%;
  height: auto;
  object-fit: contain;
  background: var(--atproto-subtle);
}
.images.n-2 { grid-template-columns: 1fr 1fr; }
.images.n-3 { grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; }
.images.n-3 .img-0 { grid-row: 1 / span 2; }
.images.n-4 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
.images.n-2 img, .images.n-3 img, .images.n-4 img {
  width: 100%; height: 100%; object-fit: cover; display: block; aspect-ratio: 16/9;
  background: var(--atproto-border);
}

.video-embed {
  margin-top: var(--atproto-space-2);
  border-radius: var(--atproto-radius-inner);
  overflow: hidden;
  background: #000;
}
.video-embed video { width: 100%; max-height: 520px; display: block; background: #000; }
.video-embed .video-fallback {
  padding: var(--atproto-space-3);
  background: var(--atproto-bg);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}

.external {
  display: grid;
  grid-template-columns: 1fr;
  margin-top: var(--atproto-space-2);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  color: inherit;
  text-decoration: none;
  overflow: hidden;
}
.external.has-thumb { grid-template-columns: 100px 1fr; }
.external.has-thumb .ext-thumb {
  width: 100px;
  height: 100px;
  object-fit: cover;
  background: var(--atproto-border);
}
.external:hover { background: var(--atproto-hover-bg); }
.external .ext-body { padding: var(--atproto-space-3); min-width: 0; }
.external .ext-title { font-weight: var(--atproto-font-weight-semibold); }
.external .ext-desc {
  color: var(--atproto-muted);
  font-size: 0.9em;
  margin-top: var(--atproto-space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.external .ext-host {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-xs);
  margin-top: var(--atproto-space-1);
}

.quote {
  margin: var(--atproto-space-2) 0 0;
  padding: 0;
  border-radius: var(--atproto-radius-inner);
  overflow: hidden;
}
.quote atproto-post { display: block; }

.counts {
  display: flex;
  gap: clamp(var(--atproto-space-3), 3vw, var(--atproto-space-5));
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  padding-top: var(--atproto-space-1);
  flex-wrap: wrap;
}
.counts b {
  color: var(--atproto-text);
  font-weight: var(--atproto-font-weight-semibold);
  margin-right: var(--atproto-space-1);
}
:host([compact]) .counts, :host([no-counts]) .counts { display: none; }

/* Stack on narrow containers — kicks in BEFORE display-name + handle would
   collide with the avatar at the default 40px. The styling demo grid columns
   land in the 260-340px range, so the threshold needs to be high enough to
   catch them. */
@container (max-width: 380px) {
  article { grid-template-columns: 1fr; column-gap: 0; }
  .avatar-link { grid-row: auto; }
  .body { grid-column: auto; }
  .counts { gap: var(--atproto-space-3); font-size: var(--atproto-font-size-xs); }
  .author { font-size: var(--atproto-font-size-sm); }
}
`;function F(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function fr(r,f,n){let v=n.ref.$link;return`${r}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(f)}&cid=${encodeURIComponent(v)}`}function Cn(r){let f=new Date(r).getTime(),n=Math.max(0,Date.now()-f),v=Math.floor(n/1000);if(v<60)return`${v}s`;let $=Math.floor(v/60);if($<60)return`${$}m`;let y=Math.floor($/60);if(y<24)return`${y}h`;let u=Math.floor(y/24);if(u<7)return`${u}d`;return new Date(r).toLocaleDateString()}function Sn(r,f){return`https://bsky.app/profile/${encodeURIComponent(r)}/post/${encodeURIComponent(f)}`}class ff extends W{static observedAttributes=["src","compact","no-counts","constellation"];errorCss(){return rr}loadingSkeleton(){let f=this.hasAttribute("compact")?24:40;return`<article part="loading" aria-busy="true" role="status">
      <span class="sr-only">Loading post…</span>
      <div class="skeleton-circle" style="width:${f}px;height:${f}px;grid-row:1/span 3"></div>
      <div class="skeleton-bar short" style="grid-column:2"></div>
      <div class="skeleton-bar" style="grid-column:2"></div>
      <div class="skeleton-bar" style="grid-column:2;width:80%"></div>
    </article>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute",rr,"permanent");return}this.paintLoading(rr);let n=this.getAttribute("constellation")??void 0,v=await B(f,{signal:r.signal}),$=J(v),u=this.hasAttribute("no-counts")||this.hasAttribute("compact")?Promise.resolve([0,0,0,0]):Promise.all([Q($,m.like.collection,m.like.path,{signal:r.signal,...n?{endpoint:n}:{}}).catch(()=>0),Q($,m.repost.collection,m.repost.path,{signal:r.signal,...n?{endpoint:n}:{}}).catch(()=>0),Q($,m.reply.collection,m.reply.path,{signal:r.signal,...n?{endpoint:n}:{}}).catch(()=>0),Q($,m.quote.collection,m.quote.path,{signal:r.signal,...n?{endpoint:n}:{}}).catch(()=>0)]),[w,z,L,K,Y]=await Promise.all([N(v.did,v.collection,v.rkey,{signal:r.signal}),cn(v.did,r.signal),V(v.did,{signal:r.signal}),N(v.did,"app.bsky.actor.profile","self",{signal:r.signal}).catch(()=>null),u]);this.paint(this.renderPost(v,w,z,L,K,Y),rr)}renderPost(r,f,n,v,$,y){let u=f.value,[w=0,z=0,L=0,K=0]=y,Y=$?.value.displayName??n,P=$?.value.avatar?fr(v,r.did,$.value.avatar):"",_=Sn(n,r.rkey),j=P?`<div part="avatar" class="avatar"><img part="avatar-image" src="${F(P)}" alt=""></div>`:'<div part="avatar" class="avatar" aria-hidden="true"></div>',q=S(u.text,u.facets),I=this.renderEmbed(u.embed,r.did,v);return`
<article part="article">
  <a part="avatar-link" class="avatar-link" href="${F(_)}" rel="noopener noreferrer" target="_blank" aria-label="View post by ${F(Y)}">${j}</a>
  <header part="author" class="author">
    <a href="${F(_)}" rel="noopener noreferrer" target="_blank">
      <span part="display-name" class="display-name">${F(Y)}</span>
      <span part="handle" class="handle">@${F(n)}</span>
      <time part="time" class="time" datetime="${F(u.createdAt)}">${Cn(u.createdAt)}</time>
    </a>
  </header>
  <div part="body" class="body">
    <div part="text" class="text">${q}</div>
    ${I}
    <div part="counts" class="counts">
      <span part="count"><b>${L.toLocaleString()}</b> replies</span>
      <span part="count"><b>${z.toLocaleString()}</b> reposts</span>
      <span part="count"><b>${K.toLocaleString()}</b> quotes</span>
      <span part="count"><b>${w.toLocaleString()}</b> likes</span>
    </div>
  </div>
</article>`}renderEmbed(r,f,n){if(!r)return"";if(Yn(r))return Ln(r,f,n);if(Zn(r))return Wn(r,f,n);if(Pn(r))return hn(r,f,n);if(dn(r))return Kn(r.record.uri);if(sn(r)){let v=r.media,$="";if(Yn(v))$=Ln(v,f,n);else if(Zn(v))$=Wn(v,f,n);else if(Pn(v))$=hn(v,f,n);return $+Kn(r.record.record.uri)}return""}}function Ln(r,f,n){let v=r.images.length,$=r.images.map((y,u)=>{let w=fr(n,f,y.image),z=y.alt?F(y.alt):"";return`<img part="image" class="img-${u}" src="${F(w)}" alt="${z}" loading="lazy">`}).join("");return`<div part="images" class="images n-${v}">${$}</div>`}function Wn(r,f,n){let v=r.external,$=O(v.uri),y="";try{y=new URL(v.uri).host}catch{}let u=v.thumb?`<img part="external-thumb" class="ext-thumb" src="${F(fr(n,f,v.thumb))}" alt="" loading="lazy">`:"";return`
<a part="external" class="external${v.thumb?" has-thumb":""}" href="${F($)}" rel="noopener noreferrer" target="_blank">
  ${u}
  <div class="ext-body">
    <div part="external-title" class="ext-title">${F(v.title)}</div>
    <div part="external-desc" class="ext-desc">${F(v.description)}</div>
    <div part="external-host" class="ext-host">${F(y)}</div>
  </div>
</a>`}function hn(r,f,n){let v=fr(n,f,r.video),$=r.alt?F(r.alt):"",y=r.video.mimeType||"video/mp4",u=/^video\/(mp4|webm|ogg)/i.test(y),w=r.aspectRatio?`aspect-ratio: ${r.aspectRatio.width}/${r.aspectRatio.height};`:"";if(!u)return`<div part="video" class="video-embed"><div class="video-fallback">Video (${F(y)}) — <a href="${F(O(v))}" rel="noopener noreferrer" target="_blank">download</a>${$?` · ${$}`:""}</div></div>`;return`
<div part="video" class="video-embed">
  <video controls playsinline preload="metadata" style="${w}" ${$?`aria-label="${$}"`:""}>
    <source src="${F(v)}" type="${F(y)}">
    Your browser does not support the video element.
  </video>
</div>`}function Kn(r){try{x(r)}catch{return""}return`<blockquote part="quote" class="quote" cite="${F(r)}"><atproto-post src="${F(r)}" compact></atproto-post></blockquote>`}function Yn(r){return r.$type==="app.bsky.embed.images"}function Zn(r){return r.$type==="app.bsky.embed.external"}function dn(r){return r.$type==="app.bsky.embed.record"}function sn(r){return r.$type==="app.bsky.embed.recordWithMedia"}function Pn(r){return r.$type==="app.bsky.embed.video"}async function cn(r,f){let v=(await G(r,f?{signal:f}:{})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function nf(r="atproto-post"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,ff)}var nr=`
${h}
article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  box-shadow: var(--atproto-shadow);
  overflow: hidden;
  max-width: var(--atproto-max-width);
  transition: var(--atproto-transition);
}
.banner {
  width: 100%;
  height: 140px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--atproto-accent) 25%, transparent), var(--atproto-border));
}
.banner img { width: 100%; height: 100%; object-fit: cover; display: block; }
.head {
  padding: var(--atproto-space-4);
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: var(--atproto-space-4);
  row-gap: var(--atproto-space-2);
}
.avatar {
  width: var(--atproto-avatar-size-lg);
  height: var(--atproto-avatar-size-lg);
  margin-top: -50px;
  border: 3px solid var(--atproto-bg);
  border-radius: 50%;
  background: var(--atproto-border);
  overflow: hidden;
  grid-row: 1 / span 2;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.names {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding-top: var(--atproto-space-1);
  min-width: 0;
}
.names a { color: inherit; text-decoration: none; }
.names a:hover .display-name,
.names a:hover .handle {
  text-decoration: underline;
}
.display-name {
  font-size: var(--atproto-font-size-xl);
  font-weight: var(--atproto-font-weight-bold);
  line-height: var(--atproto-line-height-tight);
  letter-spacing: var(--atproto-letter-spacing-tight);
  word-break: break-word;
}
.handle {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  word-break: break-word;
}
.description {
  grid-column: 1 / -1;
  white-space: pre-wrap;
  color: var(--atproto-text);
  margin-top: var(--atproto-space-1);
  word-wrap: break-word;
}
.stats {
  display: flex;
  gap: var(--atproto-space-6);
  padding: var(--atproto-space-3) var(--atproto-space-4);
  border-top: 1px solid var(--atproto-border);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  flex-wrap: wrap;
}
.stats b {
  color: var(--atproto-text);
  font-weight: var(--atproto-font-weight-bold);
  margin-right: var(--atproto-space-1);
}
`;function k(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function qn(r,f,n){return`${r}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(f)}&cid=${encodeURIComponent(n.ref.$link)}`}async function en(r,f){if(r.startsWith("did:"))return r;if(r.startsWith("at://")){let n=r.slice(5).split("/")[0];if(!n)throw Error(`invalid at-uri: ${r}`);return n.startsWith("did:")?n:await Z(n,f?{signal:f}:{})}return await Z(r,f?{signal:f}:{})}async function rv(r,f){let v=(await G(r,f?{signal:f}:{})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}async function Nn(r,f,n,v){let $=0,y;for(let u=0;u<10;u++){let w=await H(r,f,{limit:100,...y?{cursor:y}:{},signal:v});if($+=w.records.length,$>=n)return{exact:!1,value:n};if(!w.cursor||w.records.length===0)return{exact:!0,value:$};y=w.cursor}return{exact:!1,value:n}}function Xn(r){if(r.exact)return r.value.toLocaleString();return`${r.value.toLocaleString()}+`}class vf extends W{static observedAttributes=["src","constellation"];errorCss(){return nr}loadingSkeleton(){return`<article part="loading" aria-busy="true" role="status">
      <span class="sr-only">Loading profile…</span>
      <div class="skeleton-block" style="height:140px;width:100%"></div>
      <div class="head">
        <div class="skeleton-circle" style="width:80px;height:80px;margin-top:-50px;border:3px solid var(--atproto-bg);grid-row:1/span 2"></div>
        <div class="skeleton-bar" style="width:50%;margin-top:8px"></div>
        <div class="skeleton-bar short"></div>
      </div>
      <div class="stats">
        <div class="skeleton-bar short" style="width:70px;height:0.9rem"></div>
        <div class="skeleton-bar short" style="width:70px;height:0.9rem"></div>
        <div class="skeleton-bar short" style="width:70px;height:0.9rem"></div>
      </div>
    </article>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle, did, or at-uri)",nr,"permanent");return}this.paintLoading(nr);let n=this.getAttribute("constellation")??void 0,v=await en(f,r.signal),[$,y,u,w,z,L]=await Promise.all([N(v,"app.bsky.actor.profile","self",{signal:r.signal}).catch(()=>null),rv(v,r.signal),V(v,{signal:r.signal}),Q(v,m.follow.collection,m.follow.path,{signal:r.signal,...n?{endpoint:n}:{}}).catch(()=>0),Nn(v,"app.bsky.graph.follow",500,r.signal).catch(()=>({exact:!1,value:0})),Nn(v,"app.bsky.feed.post",500,r.signal).catch(()=>({exact:!1,value:0}))]);this.paint(this.render(v,y,u,$,w,z,L),nr)}render(r,f,n,v,$,y,u){let w=v?.value,z=w?.displayName??f,L=w?.description??"",K=w?.avatar?qn(n,r,w.avatar):"",Y=w?.banner?qn(n,r,w.banner):"",P=`https://bsky.app/profile/${encodeURIComponent(f)}`;return`
<article part="article">
  <div part="banner" class="banner">${Y?`<img part="banner-image" src="${k(Y)}" alt="">`:""}</div>
  <div part="head" class="head">
    <div part="avatar" class="avatar">${K?`<img part="avatar-image" src="${k(K)}" alt="">`:""}</div>
    <div part="names" class="names">
      <a href="${k(P)}" rel="noopener noreferrer" target="_blank">
        <span part="display-name" class="display-name">${k(z)}</span>
        <span part="handle" class="handle">@${k(f)}</span>
      </a>
    </div>
    ${L?`<div part="description" class="description">${k(L)}</div>`:""}
  </div>
  <div part="stats" class="stats">
    <span part="stat"><b>${$.toLocaleString()}</b> followers</span>
    <span part="stat"><b>${Xn(y)}</b> following</span>
    <span part="stat"><b>${Xn(u)}</b> posts</span>
  </div>
</article>`}}function $f(r="atproto-profile"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,vf)}var vr=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.feed {
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-3);
  list-style: none;
  padding: 0;
  margin: 0;
}
.feed-item { display: block; }
.repost-label {
  display: flex;
  align-items: center;
  gap: var(--atproto-space-1);
  padding: 0 var(--atproto-space-4) var(--atproto-space-1);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-xs);
}
.repost-label::before {
  content: "↻";
  font-weight: var(--atproto-font-weight-bold);
}
.repost-label a { color: inherit; text-decoration: none; }
.repost-label a:hover { text-decoration: underline; }
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  margin-top: var(--atproto-space-2);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
.empty {
  padding: var(--atproto-space-4);
  color: var(--atproto-muted);
  text-align: center;
  font-size: var(--atproto-font-size-sm);
}
`,fv=10;function Qn(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}class yf extends W{static observedAttributes=["src","collection","limit","include-replies","include-reposts"];#r=null;#f=null;#n;#v;#$=!1;#y=!1;#u=null;errorCss(){return vr}loadingSkeleton(){let r=(f="80%")=>`<div class="feed-item" style="border:1px solid var(--atproto-border);border-radius:var(--atproto-radius);padding:var(--atproto-space-4);display:flex;gap:var(--atproto-space-3)">
        <div class="skeleton-circle" style="width:40px;height:40px;flex-shrink:0"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:var(--atproto-space-2)">
          <div class="skeleton-bar short"></div>
          <div class="skeleton-bar" style="width:${f}"></div>
        </div>
      </div>`;return`<div part="loading" class="feed" role="status" aria-busy="true"><span class="sr-only">Loading feed…</span>${r("90%")}${r("75%")}</div>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",vr,"permanent");return}this.#n=void 0,this.#v=void 0,this.#$=!1,this.#y=!1,this.#u=r.signal,this.paintLoading(vr),this.#r=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),this.#f=await this.#z(this.#r,r.signal),this.root.innerHTML=`<style>${vr}</style>
      <ol part="feed" class="feed" role="feed"></ol>
      <button part="loadmore" class="loadmore" type="button">Load more</button>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#w()),await this.#w()}async#z(r,f){let v=(await G(r,{signal:f})).alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}async#w(){if(!this.#r||!this.#u)return;if(this.#$&&this.#y)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".feed");if(!f||!r)return;r.disabled=!0,r.textContent="Loading…";let n=Number(this.getAttribute("limit"))||fv,v=this.getAttribute("collection")??"app.bsky.feed.post",$=this.hasAttribute("include-replies"),y=!this.hasAttribute("no-reposts")&&v==="app.bsky.feed.post";try{let u=this.#$?Promise.resolve({entries:[],cursor:void 0,done:!0}):this.#m(v,n,$,this.#u),w=!y||this.#y?Promise.resolve({entries:[],cursor:void 0,done:!0}):this.#L(n,this.#u),[z,L]=await Promise.all([u,w]);this.#n=z.cursor,this.#$=z.done,this.#v=L.cursor,this.#y=L.done;let K=[...z.entries,...L.entries].sort((P,_)=>P.createdAt<_.createdAt?1:-1).slice(0,n);for(let P of K){let _=document.createElement("li");if(_.className="feed-item",_.setAttribute("part","feed-item"),P.kind==="repost"&&this.#f){let q=document.createElement("header");q.className="repost-label",q.setAttribute("part","repost-label");let I=Qn(this.#f);q.innerHTML=`<span>Reposted by <a href="https://bsky.app/profile/${encodeURIComponent(this.#f)}" rel="noopener noreferrer" target="_blank">@${I}</a></span>`,_.appendChild(q)}let j=document.createElement("atproto-post");j.setAttribute("src",P.uri),j.setAttribute("no-counts",""),j.setAttribute("part","post"),_.appendChild(j),f.appendChild(_)}if(f.children.length===0)f.innerHTML=`<div part="empty" class="empty">no records in ${Qn(v)}</div>`;let Y=this.#$&&this.#y;r.disabled=Y,r.textContent=Y?"End of feed":"Load more"}catch(u){r.disabled=!1,r.textContent="Retry";let w=u instanceof Error?u.message:String(u),z=document.createElement("div");z.className="empty",z.setAttribute("part","empty"),z.textContent=`error loading feed: ${w}`,f.appendChild(z)}}async#m(r,f,n,v){let $=await H(this.#r,r,{limit:Math.min(100,f*3),...this.#n?{cursor:this.#n}:{},signal:v});return{entries:$.records.filter((u)=>n||!u.value||!u.value.reply).slice(0,f).map((u)=>({kind:"post",uri:u.uri,createdAt:u.value?.createdAt??""})),cursor:$.cursor,done:!$.cursor||$.records.length===0}}async#L(r,f){let n=await H(this.#r,"app.bsky.feed.repost",{limit:r,...this.#v?{cursor:this.#v}:{},signal:f});return{entries:n.records.filter(($)=>!!$.value?.subject?.uri).map(($)=>({kind:"repost",uri:$.value.subject.uri,createdAt:$.value.createdAt??"",repostedBy:this.#f??this.#r??""})),cursor:n.cursor,done:!n.cursor||n.records.length===0}}}function uf(r="atproto-feed"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,yf)}var $r=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.thread {
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-2);
  list-style: none;
  padding: 0;
  margin: 0;
}
.reply {
  display: block;
  border-left: 2px solid var(--atproto-border);
  padding-left: var(--atproto-space-3);
}
.reply atproto-post { display: block; }
.reply atproto-comments { display: block; margin-top: var(--atproto-space-2); }
.expand {
  margin-top: var(--atproto-space-1);
  padding: var(--atproto-space-1) var(--atproto-space-2);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  background: var(--atproto-bg);
  color: var(--atproto-muted);
  font: inherit;
  font-size: var(--atproto-font-size-xs);
  cursor: pointer;
}
.expand:hover {
  color: var(--atproto-text);
  background: var(--atproto-subtle);
}
.empty, .head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  padding: var(--atproto-space-1) 0;
}
.head b {
  color: var(--atproto-text);
  font-weight: var(--atproto-font-weight-semibold);
}
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
  margin-top: var(--atproto-space-2);
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
`,nv=10,vv=1;function $v(r){return`at://${r.did}/${r.collection}/${r.rkey}`}class wf extends W{static observedAttributes=["src","depth","limit","show-count","constellation"];#r=null;#f=null;#n=!1;#v=null;errorCss(){return $r}loadingSkeleton(){return`<div part="loading" class="thread" role="status" aria-busy="true">
      <span class="sr-only">Loading replies…</span>
      ${`<div class="reply">
      <div style="display:flex;gap:var(--atproto-space-2);align-items:center">
        <div class="skeleton-circle" style="width:24px;height:24px"></div>
        <div class="skeleton-bar short" style="flex:1;max-width:120px"></div>
      </div>
      <div class="skeleton-bar" style="margin-top:var(--atproto-space-2);width:90%"></div>
    </div>`}
      ${`<div class="reply">
      <div style="display:flex;gap:var(--atproto-space-2);align-items:center">
        <div class="skeleton-circle" style="width:24px;height:24px"></div>
        <div class="skeleton-bar short" style="flex:1;max-width:120px"></div>
      </div>
      <div class="skeleton-bar" style="margin-top:var(--atproto-space-2);width:90%"></div>
    </div>`}
    </div>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri)",$r,"permanent");return}this.#f=null,this.#n=!1,this.#v=r.signal,x(f),this.#r=f,this.paintLoading($r);let n=this.hasAttribute("show-count");this.root.innerHTML=`<style>${$r}</style>
      ${n?'<header part="head" class="head" aria-live="polite"></header>':""}
      <ol part="thread" class="thread"></ol>
      <button part="loadmore" class="loadmore" type="button">Load replies</button>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#$()),await this.#$()}async#$(){if(!this.#r||!this.#v||this.#n)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".thread");if(!f||!r)return;r.disabled=!0,r.textContent="Loading…";let n=Number(this.getAttribute("limit"))||nv,v=Math.max(0,Number(this.getAttribute("depth")??vv)),$=this.getAttribute("constellation")??void 0;try{let y=await X(this.#r,m.reply.collection,m.reply.path,{limit:n,signal:this.#v,...this.#f?{cursor:this.#f}:{},...$?{endpoint:$}:{}}),u=this.root.querySelector(".head");if(u)u.innerHTML=`<b>${y.total.toLocaleString()}</b> repl${y.total===1?"y":"ies"}`;for(let w of y.records){let z=$v(w),L=document.createElement("li");L.className="reply",L.setAttribute("part","reply");let K=document.createElement("atproto-post");if(K.setAttribute("src",z),K.setAttribute("compact",""),L.appendChild(K),v>0){let Y=document.createElement("atproto-comments");Y.setAttribute("src",z),Y.setAttribute("depth",String(v-1)),Y.setAttribute("limit",String(n)),L.appendChild(Y)}else{let Y=document.createElement("button");Y.type="button",Y.className="expand",Y.setAttribute("part","expand"),Y.textContent="Show replies",Y.addEventListener("click",()=>{let P=document.createElement("atproto-comments");P.setAttribute("src",z),P.setAttribute("depth","0"),P.setAttribute("limit",String(n)),Y.replaceWith(P)}),L.appendChild(Y)}f.appendChild(L)}if(f.children.length===0)f.innerHTML='<div part="empty" class="empty">no replies yet</div>';if(this.#f=y.cursor,this.#n=!y.cursor||y.records.length===0,r.disabled=this.#n,r.textContent=this.#n?f.children.length===0?"":"End":"Load more",this.#n&&f.children.length===0&&!this.hasAttribute("show-count"))r.hidden=!0}catch(y){r.disabled=!1,r.textContent="Retry";let u=document.createElement("div");u.className="empty",u.setAttribute("part","empty"),u.textContent=`error loading replies: ${y instanceof Error?y.message:String(y)}`,f.appendChild(u)}}}function zf(r="atproto-comments"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,wf)}var yr=`
${h}
article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  max-width: calc(var(--atproto-max-width) + 80px);
  overflow: hidden;
}
header {
  padding: var(--atproto-space-3) var(--atproto-space-4);
  border-bottom: 1px solid var(--atproto-border);
  font-size: var(--atproto-font-size-sm);
  color: var(--atproto-muted);
  display: grid;
  gap: var(--atproto-space-1);
}
header .type {
  color: var(--atproto-accent);
  font-weight: var(--atproto-font-weight-semibold);
}
header .uri, header .cid {
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-xs);
  word-break: break-all;
}
.tree {
  padding: var(--atproto-space-3) var(--atproto-space-4);
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-xs);
  line-height: 1.6;
  overflow-x: auto;
}
.tree details { display: block; }
.tree summary {
  cursor: pointer;
  list-style: none;
  display: inline;
  color: var(--atproto-text);
}
.tree summary::-webkit-details-marker { display: none; }
.tree summary::before {
  content: "▶ ";
  color: var(--atproto-muted);
  display: inline-block;
  width: 0.9em;
}
.tree details[open] > summary::before { content: "▼ "; }
.tree .nested { padding-left: 1.25rem; }
.tree .k { color: var(--atproto-accent); }
.tree .s { color: #8f8f29; }
@media (prefers-color-scheme: dark) {
  .tree .s { color: #d4b86a; }
}
.tree .n { color: #b84c2a; }
.tree .b { color: #8c6cb6; }
.tree .u { color: var(--atproto-muted); }
.tree .p { color: var(--atproto-muted); margin-left: 0.25em; }
`;function T(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function mf(r,f){let n=f!==void 0?`<span class="k">"${T(f)}"</span>: `:"";if(r===null)return`${n}<span class="u">null</span>`;if(typeof r==="boolean")return`${n}<span class="b">${r}</span>`;if(typeof r==="number")return`${n}<span class="n">${r}</span>`;if(typeof r==="string")return`${n}<span class="s">${T(JSON.stringify(r))}</span>`;if(Array.isArray(r)){if(r.length===0)return`${n}[]`;let v=r.map(($)=>`<div>${mf($)}<span class="p">,</span></div>`).join("");return`${n}<details open><summary>[ <span class="p">${r.length} item${r.length===1?"":"s"}</span> ]</summary><div class="nested">${v}</div></details>`}if(typeof r==="object"){let v=r,$=Object.keys(v);if($.length===0)return`${n}{}`;let y=typeof v.$type==="string"?`<span class="s">"${T(v.$type)}"</span>`:`<span class="p">${$.length} keys</span>`,u=$.map((w)=>`<div>${mf(v[w],w)}<span class="p">,</span></div>`).join("");return`${n}<details open><summary>{ ${y} }</summary><div class="nested">${u}</div></details>`}return`${n}<span class="u">${T(String(r))}</span>`}class Lf extends W{static observedAttributes=["src"];errorCss(){return yr}loadingSkeleton(){let r=(f=0,n="60%")=>`<div style="padding-left:${f}px;display:flex;align-items:center;gap:var(--atproto-space-2);padding:var(--atproto-space-1) 0">
        <div class="skeleton-bar" style="height:0.7rem;width:${n}"></div>
      </div>`;return`<article part="loading" aria-busy="true" role="status">
      <span class="sr-only">Loading record…</span>
      <header>
        <div class="skeleton-bar" style="width:30%;height:0.85rem"></div>
        <div class="skeleton-bar" style="width:80%;height:0.7rem;margin-top:var(--atproto-space-1)"></div>
        <div class="skeleton-bar" style="width:50%;height:0.7rem;margin-top:var(--atproto-space-1)"></div>
      </header>
      <div class="tree">
        ${r(0,"70%")}
        ${r(20,"50%")}
        ${r(20,"65%")}
        ${r(40,"40%")}
        ${r(20,"55%")}
      </div>
    </article>`}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (at-uri)",yr,"permanent");return}this.paintLoading(yr);let n=x(f),v=await N(n.did,n.collection,n.rkey,{signal:r.signal});this.paint(this.render(v),yr)}render(r){let f=r.value,n=typeof f.$type==="string"?f.$type:"(untyped)",v=mf(f);return`
<article part="article">
  <header part="header">
    <div part="type" class="type">${T(n)}</div>
    <div part="uri" class="uri">${T(r.uri)}</div>
    <div part="cid" class="cid">cid: ${T(r.cid)}</div>
  </header>
  <div part="tree" class="tree">${v}</div>
</article>`}}function Wf(r="atproto-lexicon-viewer"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Lf)}class hf extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> like${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute (post at-uri or bsky.app url)");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=await B(f,{signal:r.signal}),y=await X(J($),m.like.collection,m.like.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.records.map((u)=>u.did),cursor:y.cursor,total:y.total}}}function Kf(r="atproto-likers"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,hf)}class Yf extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> repost${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=await B(f,{signal:r.signal}),y=await X(J($),m.repost.collection,m.repost.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.records.map((u)=>u.did),cursor:y.cursor,total:y.total}}}function Zf(r="atproto-reposters"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Yf)}var ur=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.wrap { display: flex; flex-direction: column; gap: var(--atproto-space-3); }
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.list { display: flex; flex-direction: column; gap: var(--atproto-space-2); }
.empty, .error-item {
  padding: var(--atproto-space-3);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  border: 1px dashed var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  text-align: center;
}
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-sm);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
`;function yv(r){return`at://${r.did}/${r.collection}/${r.rkey}`}class Pf extends W{static observedAttributes=["src","limit","constellation"];#r=null;#f=!1;#n=null;#v=null;errorCss(){return ur}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri or bsky.app url)",ur,"permanent");return}this.#r=null,this.#f=!1,this.#n=r.signal,this.paintLoading(ur);let n=await B(f,{signal:r.signal});this.#v=J(n),this.root.innerHTML=`<style>${ur}</style>
      <div class="wrap">
        <div part="head" class="head" aria-live="polite"></div>
        <div part="list" class="list" role="list"></div>
        <button part="loadmore" class="loadmore" type="button">Load more</button>
      </div>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#$()),await this.#$()}async#$(){if(!this.#n||!this.#v||this.#f)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".list"),n=this.root.querySelector(".head");if(!r||!f)return;r.disabled=!0,r.textContent="Loading…";let v=Number(this.getAttribute("limit"))||10,$=this.getAttribute("constellation")??void 0;try{let y=await X(this.#v,m.quote.collection,m.quote.path,{limit:v,signal:this.#n,...this.#r?{cursor:this.#r}:{},...$?{endpoint:$}:{}});if(n)n.innerHTML=`<b>${y.total.toLocaleString()}</b> quote${y.total===1?"":"s"}`;for(let u of y.records){let w=yv(u),z=document.createElement("atproto-post");z.setAttribute("src",w),z.setAttribute("compact",""),z.setAttribute("role","listitem"),z.setAttribute("part","post"),f.appendChild(z)}if(f.children.length===0)f.innerHTML='<div part="empty" class="empty">no quotes yet</div>';if(this.#r=y.cursor,this.#f=!y.cursor||y.records.length===0,r.disabled=this.#f,r.textContent=this.#f?"End":"Load more",this.#f&&f.children.length===0)r.hidden=!0}catch(y){r.disabled=!1,r.textContent="Retry";let u=document.createElement("div");u.className="error-item",u.setAttribute("part","error-item"),u.textContent=`error loading quotes: ${y instanceof Error?y.message:String(y)}`,f.appendChild(u)}}}function qf(r="atproto-quoters"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Pf)}class Nf extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> follower${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute (handle, did, or at-uri)");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=f.startsWith("did:")?f:f.startsWith("at://")?f.slice(5).split("/")[0]??f:await Z(f,{signal:r.signal});if(!$.startsWith("did:"))throw Error(`could not resolve ${f} to a DID`);let y=await Rr($,m.follow.collection,m.follow.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.dids,cursor:y.cursor,total:y.total}}}function Xf(r="atproto-followers"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Nf)}class Qf extends i{static observedAttributes=["a","b","source","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> in common`}async fetchPage(r){let f=this.getAttribute("a"),n=this.getAttribute("b");if(!f||!n)throw Error("need both `a` and `b` attributes (handle, did, or at-uri each)");let v=this.getAttribute("source")??"follow",$=m[v];if(!$)throw Error(`unknown source "${v}". Use: ${Object.keys(m).join(", ")}`);let[y,u]=await Promise.all([this.#r(f,r.signal),this.#r(n,r.signal)]),w=this.getAttribute("constellation")??void 0,z=Number(this.getAttribute("limit"))||16,L=await Tr(y,u,$.collection,$.path,{limit:z,signal:r.signal,...w?{endpoint:w}:{}});return{dids:L.dids,cursor:L.cursor??null,total:L.total}}async#r(r,f){if(r.startsWith("did:"))return r;if(r.startsWith("at://"))return r;return await Z(r,{signal:f})}}function Vf(r="atproto-mutuals"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Qf)}var wr=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  overflow: hidden;
  max-width: var(--atproto-max-width);
}
header {
  padding: var(--atproto-space-3) var(--atproto-space-4);
  border-bottom: 1px solid var(--atproto-border);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  display: grid;
  gap: var(--atproto-space-1);
}
header .subject {
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-xs);
  word-break: break-all;
}
header .total {
  color: var(--atproto-text);
  font-weight: var(--atproto-font-weight-semibold);
}
.rows {
  display: flex;
  flex-direction: column;
}
.row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: var(--atproto-space-3);
  align-items: center;
  padding: var(--atproto-space-2) var(--atproto-space-4);
  border-bottom: 1px solid var(--atproto-border);
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-sm);
}
.row:last-child { border-bottom: 0; }
.row .key { color: var(--atproto-accent); word-break: break-all; }
.row .count { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); font-variant-numeric: tabular-nums; }
.row .distinct {
  color: var(--atproto-muted);
  font-variant-numeric: tabular-nums;
  font-family: var(--atproto-font);
  font-size: var(--atproto-font-size-xs);
}
.row .distinct::before { content: "↳ "; }
.empty {
  padding: var(--atproto-space-4);
  color: var(--atproto-muted);
  text-align: center;
  font-size: var(--atproto-font-size-sm);
}
`;function Ff(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}class Gf extends W{static observedAttributes=["src","constellation"];errorCss(){return wr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (at-uri or did)",wr,"permanent");return}this.paintLoading(wr);let n=this.getAttribute("constellation")??void 0,v=await gr(f,{signal:r.signal,...n?{endpoint:n}:{}});this.paint(this.render(f,v),wr)}render(r,f){let n=Object.values(f).sort((u,w)=>w.records-u.records),v=n.reduce((u,w)=>u+w.records,0),$=n.reduce((u,w)=>u+w.distinct_dids,0),y=n.length===0?'<div part="empty" class="empty">no inbound links</div>':`<div part="rows" class="rows">${n.map((u)=>`<div part="row" class="row">
              <span part="key" class="key">${Ff(u.collection)}:${Ff(u.path.replace(/^\./,""))}</span>
              <span part="count" class="count">${u.records.toLocaleString()}</span>
              <span part="distinct" class="distinct">${u.distinct_dids.toLocaleString()} distinct</span>
            </div>`).join("")}</div>`;return`
<article part="article">
  <header part="header">
    <div part="subject" class="subject">${Ff(r)}</div>
    <div>
      <span part="total" class="total">${v.toLocaleString()}</span> inbound records
      · <span part="total-distinct" class="total">${$.toLocaleString()}</span> distinct sources
      across <span part="total" class="total">${n.length}</span> link kind${n.length===1?"":"s"}
    </div>
  </header>
  ${y}
</article>`}}function Jf(r="atproto-backlinks"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Gf)}var t=`
${h}
:host { display: inline-block; }
.count {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35ch;
  font-variant-numeric: tabular-nums;
  color: var(--atproto-accent);
  font-weight: var(--atproto-font-weight-semibold);
}
.count .label {
  color: var(--atproto-muted);
  font-weight: var(--atproto-font-weight);
}
`;class Bf extends W{static observedAttributes=["subject","source","label","constellation"];errorCss(){return t}loadingSkeleton(){return'<span part="loading" class="count" aria-busy="true"><span class="sr-only">Loading…</span><span style="display:inline-block;width:2ch;height:0.9em;background:var(--atproto-border);border-radius:var(--atproto-radius-sm)"></span></span>'}async refresh(r){let f=this.getAttribute("subject"),n=this.getAttribute("source");if(!f||!n){this.paintError("need `subject` + `source` attributes (source format: collection:path)",t,"permanent");return}let v=n.split(":");if(v.length<2||!v[0]||!v[1]){this.paintError(`source must be "collection:path", got "${n}"`,t,"permanent");return}let[$,...y]=v,u=y.join(":"),w=this.getAttribute("constellation")??void 0,z=this.getAttribute("label")??"";this.paintLoading(t);let L=await Q(f,$,u,{signal:r.signal,...w?{endpoint:w}:{}});this.paint(`<span part="count" class="count"><span part="number">${L.toLocaleString()}</span>${z?`<span part="label" class="label">${uv(z)}</span>`:""}</span>`,t)}}function uv(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function _f(r="atproto-generic-count"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Bf)}var zr=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.thread { display: flex; flex-direction: column; gap: var(--atproto-space-2); }
.ancestor {
  border-left: 2px solid var(--atproto-border);
  padding-left: var(--atproto-space-3);
  opacity: 0.85;
}
.focal {
  border: 2px solid var(--atproto-accent);
  border-radius: var(--atproto-radius);
  overflow: hidden;
  background: color-mix(in srgb, var(--atproto-accent) 4%, transparent);
}
.branch {
  border-left: 2px solid var(--atproto-border);
  padding-left: var(--atproto-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-2);
  margin-top: var(--atproto-space-2);
}
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: var(--atproto-font-weight-semibold);
  padding: var(--atproto-space-1) 0;
}
.truncated {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  padding: var(--atproto-space-2) 0 0 var(--atproto-space-3);
  font-style: italic;
}
.empty-root-hint {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  padding: var(--atproto-space-2) 0;
}
`,Vn=100;class Mf extends W{static observedAttributes=["src","depth","constellation"];errorCss(){return zr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri or bsky.app url)",zr,"permanent");return}this.paintLoading(zr);let n=await B(f,{signal:r.signal}),v=J(n),$=this.getAttribute("constellation")??void 0,u=(await N(n.did,n.collection,n.rkey,{signal:r.signal})).value?.reply?.root?.uri??v,w=await X(u,"app.bsky.feed.post","reply.root.uri",{limit:Vn,signal:r.signal,...$?{endpoint:$}:{}}),z=w.records.map((q)=>`at://${q.did}/${q.collection}/${q.rkey}`),L=await Promise.all(z.map(async(q)=>{try{let I=x(q),Jn=await N(I.did,I.collection,I.rkey,{signal:r.signal});return{uri:q,parentUri:Jn.value?.reply?.parent?.uri??null,children:[]}}catch{return null}})),K=new Map;K.set(u,{uri:u,parentUri:null,children:[]});for(let q of L){if(!q)continue;K.set(q.uri,q)}for(let q of K.values()){if(!q.parentUri)continue;let I=K.get(q.parentUri);if(I)I.children.push(q.uri)}for(let q of K.values())q.children.sort();let Y=[],P=K.get(v);while(P?.parentUri)Y.unshift(P.parentUri),P=K.get(P.parentUri);let _=Math.max(0,Number(this.getAttribute("depth")??2)),j=w.total>w.records.length;this.paint(this.render(v,Y,K,_,j),zr)}render(r,f,n,v,$){let y=f.length?`<div part="ancestors">
          <div part="head" class="head">thread · ${f.length} ancestor${f.length===1?"":"s"}</div>
          ${f.map((L)=>`<div part="ancestor" class="ancestor"><atproto-post src="${jf(L)}" compact></atproto-post></div>`).join("")}
        </div>`:"",u=n.get(r),w=u&&u.children.length>0?`<div part="replies">
          <div part="head" class="head">replies</div>
          ${this.renderBranch(u.children,n,v)}
        </div>`:'<div part="replies"><div part="head" class="head">replies</div><div class="empty-root-hint">no replies yet</div></div>',z=$?`<div class="truncated">thread exceeds ${Vn} replies — showing first page only</div>`:"";return`
<div part="thread" class="thread" role="list">
  ${y}
  <div part="focal" class="focal" role="listitem">
    <atproto-post src="${jf(r)}"></atproto-post>
  </div>
  ${w}
  ${z}
</div>`}renderBranch(r,f,n){return r.map((v)=>{let $=f.get(v),y=$&&n>0&&$.children.length>0?`<div part="branch" class="branch">${this.renderBranch($.children,f,n-1)}</div>`:"";return`<div part="reply">
          <atproto-post src="${jf(v)}" compact></atproto-post>
          ${y}
        </div>`}).join("")}}function jf(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function xf(r="atproto-thread"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Mf)}var U=`
${h}
:host { display: block; max-width: calc(var(--atproto-max-width) + 80px); }
.list {
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-3);
}
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
  margin-top: var(--atproto-space-2);
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
.empty {
  padding: var(--atproto-space-4);
  color: var(--atproto-muted);
  text-align: center;
  font-size: var(--atproto-font-size-sm);
}
`,wv=10;class If extends W{static observedAttributes=["src","collection","limit"];#r=null;#f;#n=!1;#v=null;errorCss(){return U}async refresh(r){let f=this.getAttribute("src"),n=this.getAttribute("collection");if(!f){this.paintError("missing `src` attribute (handle or did)",U,"permanent");return}if(!n){this.paintError("missing `collection` attribute (lexicon NSID)",U,"permanent");return}this.#f=void 0,this.#n=!1,this.#v=r.signal,this.paintLoading(U),this.#r=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),this.root.innerHTML=`<style>${U}</style>
      <div part="head" class="head"></div>
      <div part="list" class="list" role="list"></div>
      <button part="loadmore" class="loadmore" type="button">Load more</button>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#$()),await this.#$()}async#$(){if(!this.#r||!this.#v||this.#n)return;let r=this.getAttribute("collection"),f=this.root.querySelector(".loadmore"),n=this.root.querySelector(".list"),v=this.root.querySelector(".head");if(!f||!n)return;f.disabled=!0,f.textContent="Loading…";let $=Number(this.getAttribute("limit"))||wv;try{let y=await H(this.#r,r,{limit:$,...this.#f?{cursor:this.#f}:{},signal:this.#v});if(v)v.innerHTML=`<b>${r}</b> on ${Fn(this.#r)}`;for(let u of y.records){let w=document.createElement("atproto-lexicon-viewer");w.setAttribute("src",u.uri),w.setAttribute("role","listitem"),w.setAttribute("part","record"),n.appendChild(w)}if(n.children.length===0)n.innerHTML=`<div part="empty" class="empty">no records in ${Fn(r)}</div>`;if(this.#f=y.cursor,this.#n=!y.cursor||y.records.length===0,f.disabled=this.#n,f.textContent=this.#n?"End":"Load more",this.#n&&n.children.length===0)f.hidden=!0}catch(y){f.disabled=!1,f.textContent="Retry";let u=document.createElement("div");u.className="empty",u.setAttribute("part","empty"),u.textContent=`error: ${y instanceof Error?y.message:String(y)}`,n.appendChild(u)}}}function Fn(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Rf(r="atproto-record-list"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,If)}var p=`
${h}
:host { display: inline-block; width: auto; }
.count {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35ch;
  font-variant-numeric: tabular-nums;
  color: var(--atproto-accent);
  font-weight: var(--atproto-font-weight-semibold);
}
.count .label {
  color: var(--atproto-muted);
  font-weight: var(--atproto-font-weight);
}
`;class Hf extends W{static observedAttributes=["subject","source","label","constellation"];errorCss(){return p}loadingSkeleton(){return'<span part="loading" class="count" aria-busy="true"><span class="sr-only">Loading…</span><span style="display:inline-block;width:2ch;height:0.9em;background:var(--atproto-border);border-radius:var(--atproto-radius-sm)"></span></span>'}async refresh(r){let f=this.getAttribute("subject"),n=this.getAttribute("source");if(!f||!n){this.paintError("need `subject` + `source` attributes (source format: collection:path)",p,"permanent");return}let v=n.split(":");if(v.length<2||!v[0]||!v[1]){this.paintError(`source must be "collection:path", got "${n}"`,p,"permanent");return}let[$,...y]=v,u=y.join(":"),w=this.getAttribute("constellation")??void 0,z=this.getAttribute("label")??"";this.paintLoading(p);let L=await Hr(f,$,u,{signal:r.signal,...w?{endpoint:w}:{}});this.paint(`<span part="count" class="count"><span part="number">${L.toLocaleString()}</span>${z?`<span part="label" class="label">${zv(z)}</span>`:""}</span>`,p)}}function zv(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Tf(r="atproto-distinct-count"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Hf)}var mr=`
${h}
:host { display: block; max-width: calc(var(--atproto-max-width) + 80px); }
article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  overflow: hidden;
}
header {
  padding: var(--atproto-space-3) var(--atproto-space-4);
  border-bottom: 1px solid var(--atproto-border);
}
.handle {
  font-size: var(--atproto-font-size-lg);
  font-weight: var(--atproto-font-weight-bold);
}
.did {
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-xs);
  color: var(--atproto-muted);
  word-break: break-all;
  margin-top: var(--atproto-space-1);
}
.collections-label {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: var(--atproto-font-weight-semibold);
  padding: var(--atproto-space-3) var(--atproto-space-4) 0;
}
.collections {
  padding: var(--atproto-space-2) var(--atproto-space-3) var(--atproto-space-3);
}
.collection {
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  margin-bottom: var(--atproto-space-2);
  overflow: hidden;
}
.collection[open] { background: var(--atproto-subtle); }
.collection summary {
  list-style: none;
  cursor: pointer;
  padding: var(--atproto-space-2) var(--atproto-space-3);
  display: flex;
  align-items: center;
  gap: var(--atproto-space-2);
  font-family: var(--atproto-font-mono);
  font-size: var(--atproto-font-size-sm);
  color: var(--atproto-text);
}
.collection summary::-webkit-details-marker { display: none; }
.collection summary::before {
  content: "▶";
  color: var(--atproto-muted);
  font-size: 0.7em;
  transition: transform 0.1s;
}
.collection[open] summary::before { transform: rotate(90deg); }
.collection summary:hover { background: var(--atproto-hover-bg); }
.collection-body {
  padding: var(--atproto-space-2) var(--atproto-space-3) var(--atproto-space-3);
  border-top: 1px solid var(--atproto-border);
  background: var(--atproto-bg);
}
.empty {
  padding: var(--atproto-space-4);
  color: var(--atproto-muted);
  text-align: center;
  font-size: var(--atproto-font-size-sm);
}
`;class gf extends W{static observedAttributes=["src"];errorCss(){return mr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",mr,"permanent");return}this.paintLoading(mr);let n=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),v=await _r(n,{signal:r.signal});this.paint(this.render(v),mr)}render(r){let f=r.collections??[],n=`
<header part="header">
  <div part="handle" class="handle">@${Lr(r.handle)}</div>
  <div part="did" class="did">${Lr(r.did)}</div>
</header>`,v=f.length===0?'<div part="empty" class="empty">no collections in this repo</div>':`
<div part="collections-label" class="collections-label">${f.length} collection${f.length===1?"":"s"}</div>
<div part="collections" class="collections">
${f.map(($)=>`<details part="collection" class="collection">
  <summary part="collection-summary"><code>${Lr($)}</code></summary>
  <div part="collection-body" class="collection-body" data-lazy-for="${Lr($)}"></div>
</details>`).join("")}
</div>`;return queueMicrotask(()=>{let $=this.root,y=r.did;$.querySelectorAll("details.collection").forEach((u)=>{u.addEventListener("toggle",()=>{if(!u.open)return;let w=u.querySelector(".collection-body");if(!w||w.childElementCount>0)return;let z=w.getAttribute("data-lazy-for");if(!z)return;let L=document.createElement("atproto-record-list");L.setAttribute("src",y),L.setAttribute("collection",z),L.setAttribute("limit","5"),w.appendChild(L)},{once:!1})})}),`<article part="article">${n}${v}</article>`}}function Lr(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Af(r="atproto-repo"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,gf)}var Wr=`
${h}
:host { display: block; max-width: calc(var(--atproto-max-width) + 80px); }
.wrap {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  padding: var(--atproto-space-3) var(--atproto-space-4);
}
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  margin-bottom: var(--atproto-space-3);
}
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--atproto-space-2);
}
.tile {
  aspect-ratio: 1;
  background: var(--atproto-subtle);
  border-radius: var(--atproto-radius-inner);
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tile a, .tile video, .tile audio, .tile img {
  display: block;
  width: 100%;
  height: 100%;
}
.tile a { color: inherit; text-decoration: none; display: flex; align-items: center; justify-content: center; }
.tile video, .tile img { object-fit: cover; }
.tile audio {
  width: 100%;
  height: 40px;
  align-self: end;
  object-fit: unset;
}
.tile.kind-other, .tile.kind-audio { background: color-mix(in srgb, var(--atproto-border) 60%, transparent); }
.tile-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 3px 6px;
  font-family: var(--atproto-font-mono);
  font-size: 9px;
  color: var(--atproto-muted);
  background: color-mix(in srgb, var(--atproto-bg) 85%, transparent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  backdrop-filter: blur(4px);
}
.tile-icon {
  font-size: 1.75rem;
  opacity: 0.55;
}
.tile-icon + .tile-type {
  margin-top: var(--atproto-space-1);
  font-size: 0.7rem;
  color: var(--atproto-muted);
  font-family: var(--atproto-font-mono);
  text-align: center;
  padding: 0 var(--atproto-space-1);
  word-break: break-all;
}
.tile-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--atproto-space-2);
}
.tile.skeleton {
  background: linear-gradient(90deg, var(--atproto-border) 0%, var(--atproto-subtle) 50%, var(--atproto-border) 100%);
  background-size: 200% 100%;
  animation: atproto-shimmer 1.5s infinite linear;
}
.footer {
  margin-top: var(--atproto-space-3);
  display: flex;
  gap: var(--atproto-space-2);
}
.loadmore {
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
.empty {
  padding: var(--atproto-space-4);
  color: var(--atproto-muted);
  text-align: center;
  font-size: var(--atproto-font-size-sm);
  grid-column: 1 / -1;
}
`,mv=20;class Of extends W{static observedAttributes=["src","limit"];#r=null;#f=null;#n;#v=!1;#$=null;#y=0;errorCss(){return Wr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",Wr,"permanent");return}this.#n=void 0,this.#v=!1,this.#$=r.signal,this.#y=0,this.paintLoading(Wr),this.#r=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),this.#f=await V(this.#r,{signal:r.signal}),this.root.innerHTML=`<style>${Wr}</style>
      <div class="wrap">
        <div part="head" class="head"></div>
        <div part="grid" class="grid" role="list"></div>
        <div class="footer">
          <button part="loadmore" class="loadmore" type="button">Load more</button>
        </div>
      </div>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#u()),await this.#u()}async#u(){if(!this.#r||!this.#f||!this.#$||this.#v)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".grid"),n=this.root.querySelector(".head");if(!r||!f)return;r.disabled=!0,r.textContent="Loading…";let v=Number(this.getAttribute("limit"))||mv;try{let $=await jr(this.#r,{limit:v,...this.#n?{cursor:this.#n}:{},signal:this.#$}),y=[];for(let u of $.cids){let w=this.#m();f.appendChild(w),y.push({tile:w,cid:u})}if(this.#y+=$.cids.length,n)n.innerHTML=`<b>${this.#y.toLocaleString()}</b> blob${this.#y===1?"":"s"} shown`;if(await Promise.all(y.map(async({tile:u,cid:w})=>{let z=this.#z(w),L=await this.#w(z,this.#$).catch(()=>null),K=Lv(L);this.#L(u,z,w,L,K)})),f.children.length===0)f.innerHTML='<div part="empty" class="empty">no blobs in this repo</div>';if(this.#n=$.cursor,this.#v=!$.cursor||$.cids.length===0,r.disabled=this.#v,r.textContent=this.#v?"End":"Load more",this.#v)r.hidden=!0}catch($){r.disabled=!1,r.textContent="Retry";let y=$ instanceof Error?$.message:String($),u=document.createElement("div");u.className="empty",u.setAttribute("part","empty"),u.textContent=/501|not implemented/i.test(y)?"this PDS doesn't implement listBlobs":`error: ${y}`,f.appendChild(u)}}#z(r){return`${this.#f}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(this.#r)}&cid=${encodeURIComponent(r)}`}async#w(r,f){try{let n=await fetch(r,{method:"HEAD",signal:f});if(!n.ok)return null;return n.headers.get("content-type")}catch{return null}}#m(){let r=document.createElement("div");return r.className="tile skeleton",r.setAttribute("role","listitem"),r.setAttribute("part","tile"),r.setAttribute("aria-busy","true"),r}#L(r,f,n,v,$){r.classList.remove("skeleton"),r.classList.add(`kind-${$}`),r.removeAttribute("aria-busy"),r.setAttribute("data-mime",v??"unknown"),r.setAttribute("data-kind",$);let y=R(n.slice(-12)),u=R(n);switch($){case"image":{r.innerHTML=`
          <a href="${R(f)}" rel="noopener noreferrer" target="_blank" title="${u}">
            <img src="${R(f)}" alt="" loading="lazy">
            <div part="tile-label" class="tile-label">${y}</div>
          </a>`;return}case"video":{r.innerHTML=`
          <video controls playsinline preload="metadata" muted title="${u}">
            <source src="${R(f)}" type="${R(v??"video/mp4")}">
          </video>
          <div part="tile-label" class="tile-label">${y}</div>`;return}case"audio":{r.innerHTML=`
          <div part="tile-body" class="tile-body">
            <div part="tile-icon" class="tile-icon">${"\uD83C\uDFB5"}</div>
            <audio controls preload="metadata" title="${u}">
              <source src="${R(f)}" type="${R(v??"audio/mpeg")}">
            </audio>
          </div>
          <div part="tile-label" class="tile-label">${y}</div>`;return}case"other":{let w=v?R(v):"unknown",z=Wv(v);r.innerHTML=`
          <a href="${R(f)}" rel="noopener noreferrer" target="_blank" title="${u}">
            <div part="tile-body" class="tile-body">
              <div part="tile-icon" class="tile-icon">${z}</div>
              <div part="tile-type" class="tile-type">${w}</div>
            </div>
            <div part="tile-label" class="tile-label">${y}</div>
          </a>`;return}}}}function Lv(r){if(!r)return"other";let f=r.toLowerCase();if(f.startsWith("image/"))return"image";if(f.startsWith("video/"))return"video";if(f.startsWith("audio/"))return"audio";return"other"}function Wv(r){if(!r)return"\uD83D\uDCE6";let f=r.toLowerCase();if(f==="application/pdf")return"\uD83D\uDCC4";if(f.startsWith("application/json")||f.startsWith("text/"))return"\uD83D\uDCDD";if(f.startsWith("application/zip")||f.includes("tar")||f.includes("gzip"))return"\uD83D\uDDDC️";if(f.startsWith("font/")||f.includes("font"))return"\uD83C\uDD70️";return"\uD83D\uDCE6"}function R(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function bf(r="atproto-blobs"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Of)}var hr=`
${h}
:host { display: inline-block; width: auto; }
.commit {
  display: inline-flex;
  align-items: baseline;
  gap: 0.5ch;
  font-size: var(--atproto-font-size-sm);
  color: var(--atproto-muted);
}
.commit .rev {
  font-family: var(--atproto-font-mono);
  color: var(--atproto-text);
  font-variant-numeric: tabular-nums;
}
.commit .cid {
  font-family: var(--atproto-font-mono);
  font-size: 0.85em;
  color: var(--atproto-muted);
  opacity: 0.7;
}
.commit .age { color: var(--atproto-muted); }
`;class kf extends W{static observedAttributes=["src","show-cid","show-age"];errorCss(){return hr}loadingSkeleton(){return'<span part="loading" aria-busy="true"><span class="sr-only">Loading…</span><span style="display:inline-block;width:8ch;height:0.9em;background:var(--atproto-border);border-radius:var(--atproto-radius-sm)"></span></span>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",hr,"permanent");return}this.paintLoading(hr);let n=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),v="",$="";try{let y=await Mr(n,{signal:r.signal});v=y.rev,$=y.cid}catch(y){let u=y instanceof Error?y.message:String(y);if(!/501|not implemented/i.test(u))throw y;v=(await o(n,{signal:r.signal})).rev??""}this.paint(this.render(v,$),hr)}render(r,f){let n=this.hasAttribute("show-cid"),v=!this.hasAttribute("hide-age"),$=r?xr(r):null,y=[`<span part="rev" class="rev">${Kr(r)}</span>`];if(v&&$)y.push(`<time part="age" class="age" datetime="${Kr($.toISOString())}">· ${Kr(hv($))}</time>`);if(n&&f)y.push(`<span part="cid" class="cid">${Kr(f.slice(0,10))}…</span>`);return`<span part="commit" class="commit">${y.join("")}</span>`}}function hv(r){let f=Math.max(0,Date.now()-r.getTime()),n=Math.floor(f/1000);if(n<60)return`${n}s ago`;let v=Math.floor(n/60);if(v<60)return`${v}m ago`;let $=Math.floor(v/60);if($<24)return`${$}h ago`;let y=Math.floor($/24);if(y<7)return`${y}d ago`;return r.toLocaleDateString()}function Kr(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function af(r="atproto-latest-commit"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,kf)}var Yr=`
${h}
:host { display: inline-block; width: auto; }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35ch;
  padding: 0.15rem 0.5rem;
  border-radius: var(--atproto-radius-pill);
  font-size: var(--atproto-font-size-xs);
  font-weight: var(--atproto-font-weight-semibold);
  letter-spacing: 0.03em;
  text-transform: uppercase;
  border: 1px solid currentColor;
}
.badge.active { color: #059669; }
.badge.inactive { color: #b45309; }
.badge.blocked { color: #b91c1c; }
@media (prefers-color-scheme: dark) {
  .badge.active { color: #34d399; }
  .badge.inactive { color: #fbbf24; }
  .badge.blocked { color: #f87171; }
}
.badge::before {
  content: "";
  width: 0.5em;
  height: 0.5em;
  border-radius: 50%;
  background: currentColor;
}
`;class of extends W{static observedAttributes=["src"];errorCss(){return Yr}loadingSkeleton(){return'<span part="loading" aria-busy="true"><span class="sr-only">Loading…</span><span style="display:inline-block;width:5ch;height:1em;background:var(--atproto-border);border-radius:var(--atproto-radius-pill)"></span></span>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",Yr,"permanent");return}this.paintLoading(Yr);let n=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),v=await o(n,{signal:r.signal}),$=v.status??(v.active?"active":"inactive"),y=Kv($);this.paint(`<span part="badge" class="badge ${y}">${Yv($)}</span>`,Yr)}}function Kv(r){let f=r.toLowerCase();if(f==="active")return"active";if(f==="takendown"||f==="suspended")return"blocked";return"inactive"}function Yv(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Ef(r="atproto-repo-status"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,of)}class Df extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> mention${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute (handle or did)");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),y=await X($,m.mention.collection,m.mention.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.records.map((u)=>u.did),cursor:y.cursor,total:y.total}}}function tf(r="atproto-mentions"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Df)}var Zr=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.wrap { display: flex; flex-direction: column; gap: var(--atproto-space-3); }
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.list {
  display: flex;
  flex-direction: column;
  gap: var(--atproto-space-2);
  list-style: none;
  padding: 0;
  margin: 0;
}
.list li { display: block; }
.empty, .error-item {
  padding: var(--atproto-space-3);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  border: 1px dashed var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  text-align: center;
}
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
`;function Zv(r){return`at://${r.did}/${r.collection}/${r.rkey}`}class Uf extends W{static observedAttributes=["src","limit","constellation"];#r=null;#f=!1;#n=null;#v=null;errorCss(){return Zr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (a URL)",Zr,"permanent");return}this.#r=null,this.#f=!1,this.#n=r.signal,this.#v=f,this.paintLoading(Zr),this.root.innerHTML=`<style>${Zr}</style>
      <div class="wrap">
        <header part="head" class="head" aria-live="polite"></header>
        <ol part="list" class="list" role="list"></ol>
        <button part="loadmore" class="loadmore" type="button">Load more</button>
      </div>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#$()),await this.#$()}async#$(){if(!this.#n||!this.#v||this.#f)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".list"),n=this.root.querySelector(".head");if(!r||!f)return;r.disabled=!0,r.textContent="Loading…";let v=Number(this.getAttribute("limit"))||10,$=this.getAttribute("constellation")??void 0;try{let y=await X(this.#v,m.citation.collection,m.citation.path,{limit:v,signal:this.#n,...this.#r?{cursor:this.#r}:{},...$?{endpoint:$}:{}});if(n)n.innerHTML=`<b>${y.total.toLocaleString()}</b> citation${y.total===1?"":"s"}`;for(let u of y.records){let w=Zv(u),z=document.createElement("li");z.setAttribute("part","item");let L=document.createElement("atproto-post");L.setAttribute("src",w),L.setAttribute("compact",""),z.appendChild(L),f.appendChild(z)}if(f.children.length===0)f.innerHTML='<li part="empty" class="empty">no posts have cited this URL yet</li>';if(this.#r=y.cursor,this.#f=!y.cursor||y.records.length===0,r.disabled=this.#f,r.textContent=this.#f?"End":"Load more",this.#f&&f.children.length===0)r.hidden=!0}catch(y){r.disabled=!1,r.textContent="Retry";let u=document.createElement("li");u.className="error-item",u.setAttribute("part","error-item"),u.textContent=`error loading citations: ${y instanceof Error?y.message:String(y)}`,f.appendChild(u)}}}function pf(r="atproto-citations"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Uf)}var Pr=`
${h}
:host { display: block; max-width: var(--atproto-max-width); }
.wrap { display: flex; flex-direction: column; gap: var(--atproto-space-2); }
.head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
}
.head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
.lists {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--atproto-space-2);
  list-style: none;
  padding: 0;
  margin: 0;
}
.list-card {
  display: block;
}
.list-card a {
  display: block;
  padding: var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  text-decoration: none;
}
.list-card a:hover { border-color: var(--atproto-accent); }
.list-name {
  font-weight: var(--atproto-font-weight-semibold);
  font-size: var(--atproto-font-size);
  word-break: break-word;
}
.list-owner {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  margin-top: var(--atproto-space-1);
  word-break: break-word;
}
.list-purpose {
  margin-top: var(--atproto-space-1);
  font-size: var(--atproto-font-size-xs);
  color: var(--atproto-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.empty {
  padding: var(--atproto-space-3);
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  text-align: center;
  border: 1px dashed var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
}
.loadmore {
  align-self: flex-start;
  padding: var(--atproto-space-1) var(--atproto-space-3);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-bg);
  color: var(--atproto-text);
  font: inherit;
  font-size: var(--atproto-font-size-sm);
  cursor: pointer;
  margin-top: var(--atproto-space-2);
}
.loadmore:hover { background: var(--atproto-hover-bg); }
.loadmore[disabled] { opacity: 0.5; cursor: default; }
`;function Pv(r){return`at://${r.did}/${r.collection}/${r.rkey}`}function qv(r){if(!r)return"";return r.replace(/^app\.bsky\.graph\.defs#/,"").replace(/([A-Z])/g," $1").trim().toLowerCase()}class lf extends W{static observedAttributes=["src","limit","constellation"];#r=null;#f=null;#n=!1;#v=null;errorCss(){return Pr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (handle or did)",Pr,"permanent");return}this.#f=null,this.#n=!1,this.#v=r.signal,this.paintLoading(Pr),this.#r=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),this.root.innerHTML=`<style>${Pr}</style>
      <section class="wrap">
        <header part="head" class="head" aria-live="polite"></header>
        <ul part="lists" class="lists" role="list"></ul>
        <button part="loadmore" class="loadmore" type="button">Load more</button>
      </section>`,this.root.querySelector(".loadmore")?.addEventListener("click",()=>void this.#$()),await this.#$()}async#$(){if(!this.#r||!this.#v||this.#n)return;let r=this.root.querySelector(".loadmore"),f=this.root.querySelector(".lists"),n=this.root.querySelector(".head");if(!r||!f)return;r.disabled=!0,r.textContent="Loading…";let v=Number(this.getAttribute("limit"))||10,$=this.getAttribute("constellation")??void 0;try{let y=await X(this.#r,m.listMember.collection,m.listMember.path,{limit:v,signal:this.#v,...this.#f?{cursor:this.#f}:{},...$?{endpoint:$}:{}});if(n)n.innerHTML=`<b>${y.total.toLocaleString()}</b> list membership${y.total===1?"":"s"}`;let u=await Promise.all(y.records.map(async(w)=>{let z=Pv(w);try{let K=(await N(w.did,"app.bsky.graph.listitem",w.rkey,{signal:this.#v})).value.list,Y=x(K),[P,_]=await Promise.all([N(Y.did,Y.collection,Y.rkey,{signal:this.#v}).catch(()=>null),Nv(Y.did,this.#v)]);return{listitemUri:z,listUri:K,parsed:Y,listRec:P,ownerHandle:_}}catch{return null}}));for(let w of u){if(!w)continue;let z=document.createElement("li");z.className="list-card",z.setAttribute("part","list-card"),z.innerHTML=Xv(w),f.appendChild(z)}if(f.children.length===0)f.innerHTML='<li part="empty" class="empty">not on any public lists</li>';if(this.#f=y.cursor,this.#n=!y.cursor||y.records.length===0,r.disabled=this.#n,r.textContent=this.#n?"End":"Load more",this.#n)r.hidden=!0}catch(y){r.disabled=!1,r.textContent="Retry";let u=document.createElement("li");u.className="empty",u.setAttribute("part","empty"),u.textContent=`error: ${y instanceof Error?y.message:String(y)}`,f.appendChild(u)}}}async function Nv(r,f){let v=(await G(r,{signal:f}).catch(()=>null))?.alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function Xv(r){let f=qr(r.listRec?.value.name??"(unnamed list)"),n=qv(r.listRec?.value.purpose),v=`https://bsky.app/profile/${encodeURIComponent(r.ownerHandle)}/lists/${encodeURIComponent(r.parsed.rkey)}`;return`
    <a href="${qr(v)}" rel="noopener noreferrer" target="_blank">
      <div part="list-name" class="list-name">${f}</div>
      <div part="list-owner" class="list-owner">by @${qr(r.ownerHandle)}</div>
      ${n?`<div part="list-purpose" class="list-purpose">${qr(n)}</div>`:""}
    </a>`}function qr(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function Cf(r="atproto-list-memberships"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,lf)}var Nr=`
${E}
article {
  background: var(--atproto-bg);
  border: 1px solid var(--atproto-border);
  border-radius: var(--atproto-radius);
  overflow: hidden;
  max-width: var(--atproto-max-width);
}
header {
  padding: var(--atproto-space-3) var(--atproto-space-4);
  display: flex;
  gap: var(--atproto-space-3);
  align-items: flex-start;
  border-bottom: 1px solid var(--atproto-border);
}
.avatar {
  width: 60px;
  height: 60px;
  border-radius: var(--atproto-radius-inner);
  background: var(--atproto-border);
  overflow: hidden;
  flex-shrink: 0;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.meta { flex: 1; min-width: 0; }
.name { font-size: var(--atproto-font-size-lg); font-weight: var(--atproto-font-weight-bold); word-break: break-word; }
.purpose {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: var(--atproto-space-1);
}
.owner { color: var(--atproto-muted); font-size: var(--atproto-font-size-sm); margin-top: var(--atproto-space-1); }
.description {
  padding: 0 var(--atproto-space-4) var(--atproto-space-3);
  color: var(--atproto-text);
  font-size: var(--atproto-font-size-sm);
  white-space: pre-wrap;
  line-height: 1.55;
}
.members { padding: var(--atproto-space-3) var(--atproto-space-4); }
.members-head {
  color: var(--atproto-muted);
  font-size: var(--atproto-font-size-sm);
  margin-bottom: var(--atproto-space-2);
}
.members-head b { color: var(--atproto-text); font-weight: var(--atproto-font-weight-semibold); }
`;function Qv(r,f,n){return`${r}/xrpc/com.atproto.sync.getBlob?did=${encodeURIComponent(f)}&cid=${encodeURIComponent(n.$link)}`}function Vv(r){if(!r)return"";return r.replace(/^app\.bsky\.graph\.defs#/,"").replace(/([A-Z])/g," $1").trim().toLowerCase()}class Sf extends W{static observedAttributes=["src","limit","constellation"];errorCss(){return Nr}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (list AT-URI)",Nr,"permanent");return}this.paintLoading(Nr);let n=x(f),v=Number(this.getAttribute("limit"))||32,$=this.getAttribute("constellation")??void 0,[y,u,w,z]=await Promise.all([N(n.did,n.collection,n.rkey,{signal:r.signal}),V(n.did,{signal:r.signal}),Fv(n.did,r.signal),X(f,m.listMember.collection,"list",{limit:v,signal:r.signal,...$?{endpoint:$}:{}})]),K=(await Promise.all(z.records.map(async(P)=>{try{return(await N(P.did,P.collection,P.rkey,{signal:r.signal})).value.subject??null}catch{return null}}))).filter((P)=>typeof P==="string"),Y=await Ar(K,r.signal);this.paint(this.render(f,y.value,u,n.did,w,Y,z.total),Nr)}render(r,f,n,v,$,y,u){let w=x(r),z=`https://bsky.app/profile/${encodeURIComponent($)}/lists/${encodeURIComponent(w.rkey)}`;return`
<article part="article">
  <header part="header">
    ${f.avatar?`<div part="avatar" class="avatar"><img src="${a(Qv(n,v,f.avatar.ref))}" alt=""></div>`:'<div part="avatar" class="avatar" aria-hidden="true"></div>'}
    <div class="meta">
      <div part="name" class="name">
        <a href="${a(z)}" rel="noopener noreferrer" target="_blank">${a(f.name??"(unnamed list)")}</a>
      </div>
      ${f.purpose?`<div part="purpose" class="purpose">${a(Vv(f.purpose))}</div>`:""}
      <div part="owner" class="owner">by @${a($)}</div>
    </div>
  </header>
  ${f.description?`<div part="description" class="description">${a(f.description)}</div>`:""}
  <section part="members" class="members">
    <div part="members-head" class="members-head"><b>${u.toLocaleString()}</b> member${u===1?"":"s"}</div>
    <div part="grid" class="grid" role="list">${y.map((K)=>`<div role="listitem">${Or(K)}</div>`).join("")}</div>
  </section>
</article>`}}async function Fv(r,f){let v=(await G(r,{signal:f}).catch(()=>null))?.alsoKnownAs?.find(($)=>$.startsWith("at://"));return v?v.slice(5):r}function a(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function df(r="atproto-list"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,Sf)}class sf extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> public block${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute (handle or did)");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),y=await X($,m.block.collection,m.block.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.records.map((u)=>u.did),cursor:y.cursor,total:y.total}}}function cf(r="atproto-blockers"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,sf)}class ef extends i{static observedAttributes=["src","limit","constellation"];headLabel(r){if(r===void 0)return"";return`<b>${r.toLocaleString()}</b> verification claim${r===1?"":"s"}`}async fetchPage(r){let f=this.getAttribute("src");if(!f)throw Error("missing `src` attribute (handle or did)");let n=this.getAttribute("constellation")??void 0,v=Number(this.getAttribute("limit"))||16,$=f.startsWith("did:")?f:await Z(f,{signal:r.signal}),y=await X($,m.verification.collection,m.verification.path,{limit:v,signal:r.signal,...r.cursor?{cursor:r.cursor}:{},...n?{endpoint:n}:{}});return{dids:y.records.map((u)=>u.did),cursor:y.cursor,total:y.total}}}function rn(r="atproto-verification"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,ef)}var Xr=`
${h}
:host { display: inline-block; width: auto; }
mark {
  display: inline-flex;
  align-items: center;
  gap: 0.35ch;
  padding: 0.15rem 0.5rem;
  border-radius: var(--atproto-radius-pill);
  font-size: var(--atproto-font-size-xs);
  font-weight: var(--atproto-font-weight-semibold);
  letter-spacing: 0.03em;
  text-transform: uppercase;
  background: var(--atproto-accent-soft);
  color: var(--atproto-accent);
  border: 1px solid color-mix(in srgb, var(--atproto-accent) 40%, transparent);
}
mark::before { content: "\uD83D\uDCCC"; }
.none { display: none; }
:host([show-when-not-pinned]) .none { display: inline; color: var(--atproto-muted); font-size: var(--atproto-font-size-xs); }
`;class fn extends W{static observedAttributes=["src","constellation","show-when-not-pinned"];errorCss(){return Xr}loadingSkeleton(){return'<span part="loading" aria-busy="true"><span class="sr-only">Loading…</span></span>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri or bsky.app url)",Xr,"permanent");return}let n=this.getAttribute("constellation")??void 0,v=await B(f,{signal:r.signal}),$=J(v);if(await Q($,m.pinnedPost.collection,m.pinnedPost.path,{signal:r.signal,...n?{endpoint:n}:{}})>0)this.paint('<mark part="badge" role="status" aria-label="Pinned post">pinned</mark>',Xr);else this.paint('<span part="none" class="none" role="status">not pinned</span>',Xr)}}function nn(r="atproto-pinned-badge"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,fn)}var Qr=`
${h}
:host { display: inline-block; width: auto; }
mark {
  display: inline-flex;
  align-items: center;
  gap: 0.35ch;
  padding: 0.15rem 0.5rem;
  border-radius: var(--atproto-radius-pill);
  font-size: var(--atproto-font-size-xs);
  font-weight: var(--atproto-font-weight-semibold);
  letter-spacing: 0.03em;
  text-transform: uppercase;
  background: color-mix(in srgb, var(--atproto-warning) 12%, transparent);
  color: var(--atproto-warning);
  border: 1px solid color-mix(in srgb, var(--atproto-warning) 40%, transparent);
}
mark::before { content: "\uD83D\uDD12"; }
.none { display: none; }
:host([show-when-absent]) .none { display: inline; color: var(--atproto-muted); font-size: var(--atproto-font-size-xs); }
`;class vn extends W{static observedAttributes=["src","kind","constellation","show-when-absent"];errorCss(){return Qr}loadingSkeleton(){return'<span part="loading" aria-busy="true"><span class="sr-only">Loading…</span></span>'}async refresh(r){let f=this.getAttribute("src");if(!f){this.paintError("missing `src` attribute (post at-uri)",Qr,"permanent");return}let n=this.getAttribute("kind")??"any",v=this.getAttribute("constellation")??void 0,$=await B(f,{signal:r.signal}),y=J($),[u,w]=await Promise.all([n==="post"?0:Q(y,m.threadgate.collection,m.threadgate.path,{signal:r.signal,...v?{endpoint:v}:{}}).catch(()=>0),n==="thread"?0:Q(y,m.postgate.collection,m.postgate.path,{signal:r.signal,...v?{endpoint:v}:{}}).catch(()=>0)]),z=u>0&&w>0?"reply + quote limits":u>0?"reply limits":w>0?"quote limits":"";if(z)this.paint(`<mark part="badge" role="status" aria-label="Has ${z}">${Gv(z)}</mark>`,Qr);else this.paint('<span part="none" class="none" role="status">open</span>',Qr)}}function Gv(r){return r.replace(/[<>&"]/g,(f)=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"})[f])}function $n(r="atproto-gate-badge"){if(typeof customElements>"u")return;if(!customElements.get(r))customElements.define(r,vn)}function Gn(){kr(),or(),Dr(),pr(),Sr(),cr(),rf(),nf(),$f(),uf(),zf(),Wf(),Kf(),Zf(),qf(),Xf(),Vf(),Jf(),_f(),xf(),Rf(),Tf(),Af(),bf(),af(),Ef(),tf(),pf(),Cf(),df(),cf(),rn(),nn(),$n()}if(typeof customElements<"u")Gn();export{xr as tidToDate,On as setConstellationEndpoint,O as safeUrl,B as resolvePostSource,V as resolvePdsEndpoint,Z as resolveHandle,G as resolveDidDocument,zn as relativeTime,rn as registerVerification,kr as registerTime,xf as registerThread,or as registerRichText,Zf as registerReposters,Ef as registerRepoStatus,Af as registerRepo,Rf as registerRecordList,qf as registerQuoters,$f as registerProfile,nf as registerPost,nn as registerPinnedBadge,Vf as registerMutuals,tf as registerMentions,Cf as registerListMemberships,df as registerList,Kf as registerLikers,rf as registerLikeCount,Wf as registerLexiconViewer,af as registerLatestCommit,pr as registerHandle,_f as registerGenericCount,$n as registerGateBadge,Xf as registerFollowers,uf as registerFeed,cr as registerEngagementRow,Tf as registerDistinctCount,Sr as registerDisplayName,zf as registerComments,pf as registerCitations,cf as registerBlockers,bf as registerBlobs,Jf as registerBacklinks,Dr as registerAvatar,Gr as parseBskyPostUrl,x as parseAtUri,H as listRecords,jr as listBlobs,Fr as isBskyPostUrl,o as getRepoStatus,N as getRecord,Tr as getManyToMany,gr as getLinksAll,Mr as getLatestCommit,Hr as getDistinctDidsCount,Rr as getDistinctDids,bn as getConstellationEndpoint,Q as getBacklinksCount,X as getBacklinks,_r as describeRepo,Gn as defineAll,Rn as clearCache,J as buildAtUri,h as THEME_CSS,m as SOURCES,Jr as CacheFetchError,ef as AtprotoVerification,br as AtprotoTime,Mf as AtprotoThread,ar as AtprotoRichText,Yf as AtprotoReposters,of as AtprotoRepoStatus,gf as AtprotoRepo,If as AtprotoRecordList,Pf as AtprotoQuoters,vf as AtprotoProfile,ff as AtprotoPost,fn as AtprotoPinnedBadge,Qf as AtprotoMutuals,Df as AtprotoMentions,lf as AtprotoListMemberships,Sf as AtprotoList,hf as AtprotoLikers,er as AtprotoLikeCount,Lf as AtprotoLexiconViewer,kf as AtprotoLatestCommit,Ur as AtprotoHandle,Bf as AtprotoGenericCount,vn as AtprotoGateBadge,Nf as AtprotoFollowers,yf as AtprotoFeed,sr as AtprotoEngagementRow,W as AtprotoElement,Hf as AtprotoDistinctCount,Cr as AtprotoDisplayName,wf as AtprotoComments,Uf as AtprotoCitations,sf as AtprotoBlockers,Of as AtprotoBlobs,Gf as AtprotoBacklinks,Er as AtprotoAvatar,i as AtprotoActorGrid};

//# debugId=F3D5D0CFDFC758EC64756E2164756E21
