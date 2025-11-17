import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


TAT_BASE = "https://tatapi.tourismthailand.org/tatapi/v5"


def tat_headers(api_key: str) -> Dict[str, str]:
    return {
        # TAT API documentation commonly uses this Authorization format
        "Authorization": f"Apikey {api_key}",
        "Accept": "application/json",
        "User-Agent": "WorldJourneyAI/1.0 (contact: maintainers)",
    }


def http_get(url: str, headers: Dict[str, str], params: Dict[str, Any], timeout: int = 15) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        if r.status_code == 200:
            return r
        # Surface useful error context
        print(f"GET {url} -> {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return None
    except requests.RequestException as e:
        print(f"GET {url} failed: {e}", file=sys.stderr)
        return None


def validate_url(url: str) -> bool:
    try:
        h = requests.head(url, timeout=10, allow_redirects=True)
        return h.status_code in (200, 301, 302)
    except requests.RequestException:
        return False


def first_image_like_url(obj: Any) -> Optional[str]:
    """Recursively scan an object for a plausible image URL from common TAT fields."""
    image_keys = {
        "web_picture", "web_picture_url", "cover_image", "cover_image_url",
        "thumbnail", "thumbnail_url", "picture", "picture_url", "image", "image_url",
    }
    if isinstance(obj, dict):
        # Direct field checks first
        for k in image_keys:
            v = obj.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
        # Gallery-like structures
        for k in ("images", "gallery", "place_images", "allimages"):
            v = obj.get(k)
            if isinstance(v, list):
                for item in v:
                    url = first_image_like_url(item)
                    if url:
                        return url
        # Fallback, recurse on values
        for v in obj.values():
            url = first_image_like_url(v)
            if url:
                return url
    elif isinstance(obj, list):
        for item in obj:
            url = first_image_like_url(item)
            if url:
                return url
    elif isinstance(obj, str):
        if obj.startswith("http") and (".jpg" in obj.lower() or ".jpeg" in obj.lower() or ".png" in obj.lower() or "?" in obj):
            return obj
    return None


def tat_search_place(api_key: str, name_th: str, province_th: str) -> Optional[Dict[str, Any]]:
    headers = tat_headers(api_key)
    # Try the explicit search endpoint first
    url_search = f"{TAT_BASE}/places/search"
    params = {"keyword": name_th, "provinceName": province_th, "language": "TH"}
    r = http_get(url_search, headers, params)
    if r is not None:
        try:
            data = r.json()
            # Common patterns: {"result":{"places":[...]}} or {"result":[...]}
            candidates = None
            if isinstance(data, dict):
                if "result" in data:
                    res = data["result"]
                    if isinstance(res, dict) and "places" in res:
                        candidates = res.get("places")
                    elif isinstance(res, list):
                        candidates = res
                elif "places" in data:
                    candidates = data["places"]
            if candidates:
                # Prefer exact province/name matches
                for c in candidates:
                    n = str(c.get("place_name") or c.get("name") or "").strip()
                    p = str(c.get("provinceName") or c.get("province") or "").strip()
                    if n and name_th in n and (not province_th or province_th in p):
                        return c
                return candidates[0]
        except ValueError:
            pass

    # Fallback to generic listing filter
    url_places = f"{TAT_BASE}/places"
    params = {"provinceName": province_th, "keyword": name_th, "language": "TH"}
    r = http_get(url_places, headers, params)
    if r is not None:
        try:
            data = r.json()
            candidates = None
            if isinstance(data, dict):
                if "result" in data:
                    res = data["result"]
                    if isinstance(res, dict) and "places" in res:
                        candidates = res.get("places")
                    elif isinstance(res, list):
                        candidates = res
                elif "places" in data:
                    candidates = data["places"]
            if candidates:
                for c in candidates:
                    n = str(c.get("place_name") or c.get("name") or "").strip()
                    p = str(c.get("provinceName") or c.get("province") or "").strip()
                    if n and name_th in n and (not province_th or province_th in p):
                        return c
                return candidates[0]
        except ValueError:
            pass

    return None


def update_imagelink_with_tat(api_key: str, file_path: Path, dry_run: bool = False, delay: float = 0.2) -> Dict[str, int]:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    places: List[Dict[str, Any]] = payload.get("places", [])

    province = payload.get("province") or "สมุทรสงคราม"

    stats = {"found": 0, "updated": 0, "validated": 0, "skipped": 0, "errors": 0}

    for pl in places:
        name_th = pl.get("name_th") or ""
        if not name_th:
            stats["skipped"] += 1
            continue

        result = tat_search_place(api_key, name_th, province)
        if not result:
            stats["skipped"] += 1
            time.sleep(delay)
            continue

        stats["found"] += 1
        url = first_image_like_url(result)
        if not url:
            stats["skipped"] += 1
            time.sleep(delay)
            continue

        if validate_url(url):
            stats["validated"] += 1
            imgs = pl.get("images") or []
            # Avoid duplicates
            if url not in imgs:
                imgs.insert(0, url)
                pl["images"] = imgs
                stats["updated"] += 1
        else:
            stats["skipped"] += 1

        time.sleep(delay)

    if not dry_run:
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats


def main():
    api_key = os.environ.get("TAT_API_KEY")
    if not api_key:
        print("Missing TAT_API_KEY environment variable. Get one from TAT Developer Portal.", file=sys.stderr)
        sys.exit(2)

    json_path = Path(__file__).parents[1] / "world_journey_ai" / "configs" / "Imagelink.json"
    dry_run = os.environ.get("DRY_RUN", "0") == "1"

    print(f"Using input file: {json_path}")
    stats = update_imagelink_with_tat(api_key, json_path, dry_run=dry_run)
    print(
        "TAT image update -> "
        f"found: {stats['found']}, updated: {stats['updated']}, "
        f"validated: {stats['validated']}, skipped: {stats['skipped']}, errors: {stats['errors']}"
    )


if __name__ == "__main__":
    main()
