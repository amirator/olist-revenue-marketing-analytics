"""Download raw Olist CSVs from public mirrors; write a manifest (URL, bytes, SHA-256, UTC time)."""
import hashlib, json, urllib.request, zipfile, io, datetime as dt
from pathlib import Path
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OFFICIAL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"
MIRROR = "https://github.com/francoc99/olist/raw/main/"
FILES = {f"olist_{n}_dataset.csv": OFFICIAL + f"olist_{n}_dataset.csv" for n in
         ["customers", "geolocation", "order_items", "order_payments", "order_reviews", "orders", "products", "sellers"]}
FILES["product_category_name_translation.csv"] = OFFICIAL + "product_category_name_translation.csv"
FILES["olist_closed_deals_dataset.csv"] = MIRROR + "olist_closed_deals_dataset.csv.zip"
FILES["olist_marketing_qualified_leads_dataset.csv"] = MIRROR + "olist_marketing_qualified_leads_dataset.csv.zip"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url in FILES.items():
        out = RAW / name
        if not out.exists():
            data = urllib.request.urlopen(url, timeout=120).read()
            if url.endswith(".zip"):
                data = zipfile.ZipFile(io.BytesIO(data)).read(name)
            out.write_bytes(data)
        b = out.read_bytes()
        manifest.append({"file": name, "url": url, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                         "checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    (RAW.parent / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} raw files ready")

if __name__ == "__main__":
    main()
