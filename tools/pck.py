import struct, sys, os

def parse(path):
    f=open(path,'rb'); head=f.read(256)
    assert head[:4]==b'GDPC', head[:4]
    version,vmaj,vmin,vpat,flags=struct.unpack_from('<IIIII',head,4)
    file_base=struct.unpack_from('<Q',head,24)[0]
    dir_off=struct.unpack_from('<Q',head,32)[0]
    # entry table may sit right after header (official) or at dir_off (community tooling)
    def try_at(o):
        f.seek(o); buf=f.read(64)
        if len(buf)<8: return None
        c=struct.unpack_from('<I',buf,0)[0]
        l=struct.unpack_from('<I',buf,4)[0]
        if 0<c<2_000_000 and 0<l<4096: return c
        return None
    count=None; base=None
    for o in (dir_off, 32+64, 32, 96):
        if o and o < os.path.getsize(path):
            c=try_at(o)
            if c: count,base=c,o; break
    if base is None: raise SystemExit("cannot locate directory")
    f.seek(base+4)
    ents=[]
    CH=1<<20
    while len(ents)<count:
        hdr=f.read(4)
        if len(hdr)<4: break
        sl=struct.unpack('<I',hdr)[0]
        raw=f.read(sl)
        pth=raw.split(b'\x00')[0].decode('utf-8','replace')
        tail=f.read(8+8+16+4)
        ofs,size=struct.unpack_from('<QQ',tail,0)
        ents.append((pth,ofs,size))
    return dict(version=version,ver=f"{vmaj}.{vmin}.{vpat}",flags=flags,
                file_base=file_base,dir_off=dir_off,count=count,entries=ents)

if __name__=='__main__':
    d=parse(sys.argv[1]); pats=[p.lower() for p in sys.argv[2:]]
    print(f"# {os.path.basename(sys.argv[1])}  pck v{d['version']} godot {d['ver']} flags={d['flags']} entries={len(d['entries'])}/{d['count']}")
    for pth,ofs,size in d['entries']:
        if pats and not any(p in pth.lower() for p in pats): continue
        print(f"{size:>10}  {pth}")

def extract(pck_path, outdir, wanted):
    d=parse(pck_path); os.makedirs(outdir, exist_ok=True)
    got=[]
    f=open(pck_path,'rb')
    for pth,ofs,size in d['entries']:
        if not any(w in pth for w in wanted): continue
        f.seek(d['file_base']+ofs if d['flags']&2 else ofs)
        data=f.read(size)
        rel = pth[2:] if pth.startswith('./') else pth.lstrip('/')
        dest=os.path.join(outdir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest,'wb').write(data); got.append(dest)
    return got
