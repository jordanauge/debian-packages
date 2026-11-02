#!/usr/bin/env python3
"""Generate separate public/private package catalogues from reprepro indexes."""
import gzip
import hashlib
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path


def packages(root):
    rows = {}
    for index in sorted((root / "dists").glob("*/**/Packages.gz")):
        suite = index.relative_to(root / "dists").parts[0]
        component = index.relative_to(root / "dists").parts[1]
        for paragraph in gzip.decompress(index.read_bytes()).decode().strip().split("\n\n"):
            fields = {}
            key = None
            for line in paragraph.splitlines():
                if line.startswith(" ") and key:
                    fields[key] += "\n" + line[1:]
                elif ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            if not fields:
                continue
            fields["Suite"], fields["Component"] = suite, component
            identity = (fields["Package"], fields["Version"], fields["Architecture"], suite, component)
            rows[identity] = fields
    return list(rows.values())


def generate(base):
    for tree in ("public", "private"):
        root = base / tree
        rows = packages(root)
        bootstrap = ""
        if tree == "public":
            candidates = [p for p in rows if p["Package"] == "synaxe-archive-keyring"]
            if candidates:
                package = candidates[0]
                source = root / package["Filename"]
                name = source.name
                shutil.copyfile(source, root / name)
                checksum = hashlib.sha256(source.read_bytes()).hexdigest()
                command = (
                    "(set -eu; d=$(mktemp -d); trap 'rm -f \"$d/" + name + "\"; rmdir \"$d\"' EXIT; "
                    'cd "$d"; curl --fail --show-error --location --proto "=https" --proto-redir "=https" '
                    "--output " + name + " https://debian.at.synaxe.org/" + name + "; "
                    "printf '%s  %s\\n' " + checksum + " " + name + " | sha256sum --check -; "
                    'if [ "$(id -u)" -eq 0 ]; then apt install --yes ./' + name + "; apt update; "
                    "else sudo apt install --yes ./" + name + "; sudo apt update; fi)"
                )
                key_info = subprocess.run(
                    ["gpg", "--batch", "--with-colons", "--show-keys", str(root / "synaxe-archive-keyring.asc")],
                    check=True, capture_output=True, text=True,
                )
                fingerprint = next(line.split(":")[9] for line in key_info.stdout.splitlines() if line.startswith("fpr:"))
                bootstrap = (
                    f'<h2>Enable the public repository</h2><p><a href="/{html.escape(name)}">'
                    f'Download {html.escape(name)}</a></p><p>SHA-256: <code>{checksum}</code></p>'
                    f'<p>Signing key fingerprint: <code>{html.escape(fingerprint)}</code></p>'
                    '<p>Copy and paste (requires curl). Trust the HTTPS site for this first install; '
                    'verify the signing fingerprint independently for stronger bootstrap trust.</p>'
                    f'<pre id="bootstrap">{html.escape(command)}</pre>'
                    '<button onclick="copyText(document.querySelector(\'#bootstrap\').textContent)">Copy install command</button>'
                    '<p><a href="/synaxe-archive-keyring.asc">Public signing key</a> | '
                    '<a href="/private/">Private packages and host profiles</a></p>'
                    '<p>Enable private access: <code>sudo apt install synaxe-archive-keyring-private</code>, '
                    'enter credentials, then <code>sudo apt update</code>.</p>'
                )
        data = json.dumps(rows).replace("<", "\\u003c")
        page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Synaxe packages</title>
<style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eee;padding:1em}
input,select,button{padding:.5em;margin:.2em}table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:.6em;border-bottom:1px solid #ccc}details{margin:.5em 0}</style>
<h1>Synaxe TREE packages</h1>BOOTSTRAP
<h2>Browse packages</h2><label>Search <input id="q" type="search"></label>
<label>Suite <select id="suite"><option value="">All</option></select></label>
<label>Component <select id="component"><option value="">All</option></select></label>
<label>Architecture <select id="arch"><option value="">All</option></select></label>
<label><input id="meta" type="checkbox">Metapackages only</label>
<label>Sort <select id="sort"><option>Package</option><option>Version</option></select></label>
<p id="count"></p><table><thead><tr><th>Package</th><th>Version</th><th>Architecture</th><th>Details</th></tr></thead>
<tbody id="rows"></tbody></table><button id="prev">Previous</button><button id="next">Next</button>
<p id="page"></p><p>Metapackages list their required packages under Dependencies.</p>
<script>
const data=DATA; let page=0;
const el=id=>document.getElementById(id);
function copyText(text){navigator.clipboard.writeText(text).catch(e=>alert("Copy failed: "+e.message));}
for(const [id,key] of [["suite","Suite"],["component","Component"],["arch","Architecture"]]){
 for(const value of [...new Set(data.map(p=>p[key]))].sort()){const o=new Option(value,value);el(id).add(o);}
}
function text(tag,value){const e=document.createElement(tag);e.textContent=value;return e;}
function render(){
 const query=el("q").value.toLowerCase();
 const rows=data.filter(p=>(p.Package+" "+p.Description).toLowerCase().includes(query)
 && (!el("suite").value||p.Suite===el("suite").value)
 && (!el("component").value||p.Component===el("component").value)
 && (!el("meta").checked||(p.Section||"").endsWith("metapackages"))
 && (!el("arch").value||p.Architecture===el("arch").value))
 .sort((a,b)=>a[el("sort").value].localeCompare(b[el("sort").value],undefined,{numeric:true}));
 const pages=Math.max(1,Math.ceil(rows.length/25));page=Math.min(page,pages-1);el("rows").replaceChildren();
 for(const p of rows.slice(page*25,(page+1)*25)){
  const tr=document.createElement("tr");for(const v of [p.Package,p.Version,p.Architecture])tr.append(text("td",v));
  const td=document.createElement("td"),d=document.createElement("details");
  d.append(text("summary",p.Description.split("\\n")[0]));
  d.append(text("pre",p.Description+"\\nDependencies: "+(p.Depends||"none")+"\\nSource: "+(p.Source||p.Package)));
  const link=document.createElement("a");link.href="./"+p.Filename;link.textContent="Download .deb";d.append(link);
  const cmd=text("button","Copy apt install");cmd.onclick=()=>copyText("sudo apt install "+p.Package);d.append(cmd);
  td.append(d);tr.append(td);el("rows").append(tr);
 }
 el("count").textContent=rows.length+" package versions";
 el("page").textContent=(page+1)+" / "+pages;
 el("prev").disabled=page===0;el("next").disabled=page===pages-1;
}
for(const id of ["q","suite","component","arch","sort","meta"])el(id).oninput=()=>{page=0;render();};
el("prev").onclick=()=>{page--;render();};el("next").onclick=()=>{page++;render();};render();
</script></html>"""
        page = page.replace("TREE", tree).replace("BOOTSTRAP", bootstrap).replace("DATA", data)
        destination = root / "index.html"
        staged = root / ".index.html.new"
        staged.write_text(page)
        staged.replace(destination)


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
