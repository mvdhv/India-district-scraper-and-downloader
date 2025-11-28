# igod_scraper.py — hybrid: requests used for states/districts, Playwright used for subdistricts/blocks
# For setup:

#   pip install requests beautifulsoup4 playwright
#   python -m playwright install chromium

import os, csv, re, time
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError

BASE_STATES = "https://igod.gov.in/sg/district/states"
ROOT = "https://igod.gov.in/"
PAGE_SIZE = 25
TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) IGOD/HybridScraper", "Accept-Language": "en-US,en;q=0.9"}

OUT_DIR = os.path.join(os.path.dirname(__file__), "data"); os.makedirs(OUT_DIR, exist_ok=True)
STAMP = datetime.now().strftime("%Y%m%d")
SUB_CSV = os.path.join(OUT_DIR, f"{STAMP}_IGOD_subdistricts.csv")
BLK_CSV = os.path.join(OUT_DIR, f"{STAMP}_IGOD_blocks.csv")
PROG_FILE = os.path.join(OUT_DIR, f"{STAMP}_IGOD_progress.txt")
LOG_FILE  = os.path.join(OUT_DIR, f"{STAMP}_IGOD.log")

def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(line + "\n")

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).replace("\xa0"," ").strip()

def abs_href(href: str) -> str:
    return urljoin(ROOT, href or "")

def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def get_expected_count(soup: BeautifulSoup) -> int | None:
    meta = soup.select_one("div.search-meta")
    if not meta: return None
    m = re.search(r"(\d+)", meta.get_text())
    return int(m.group(1)) if m else None

def write_headers_once():
    if not os.path.exists(SUB_CSV) or os.stat(SUB_CSV).st_size == 0:
        with open(SUB_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["state", "district", "subdistrict"])
    if not os.path.exists(BLK_CSV) or os.stat(BLK_CSV).st_size == 0:
        with open(BLK_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["state", "district", "block"])

def mark_done(state: str):
    with open(PROG_FILE, "a", encoding="utf-8") as f: f.write(state + "\n")

def load_done() -> set[str]:
    if not os.path.exists(PROG_FILE): return set()
    with open(PROG_FILE, encoding="utf-8") as f: return {ln.strip() for ln in f if ln.strip()}

# ---------- using requests: states & districts ----------
def get_states(session: requests.Session) -> list[tuple[str, str]]:
    soup = get_soup(session, BASE_STATES)
    return [(clean(a.get_text()), abs_href(a.get("href"))) for a in soup.select("div.cat-box.state ul li a[href]")]

def collect_district_rows_from_page(soup: BeautifulSoup) -> list[dict]:
    rows = []
    for row in soup.select("div.search-result-row, .search-row, .search-row.module, .module.search-row"):
        if "display:none" in (row.get("style","").lower()): continue
        title_el = row.select_one("a.search-title, div.search-title")
        if not title_el: continue
        name = clean(title_el.get_text())
        if not name: continue
        sub_url = block_url = None
        for b in row.select("div.search-opts a.btn-detail[href]"):
            href = abs_href(b.get("href")); txt = clean(b.get_text()).lower()
            if "/sub_districts" in href or "sub district" in txt: sub_url = href
            elif "/blocks" in href or "block" in txt: block_url = href
        rows.append({"district": name, "sub": sub_url, "block": block_url})
    return rows

def get_all_districts_for_state(session: requests.Session, state_url: str) -> list[dict]:
    all_rows, seen = [], set()
    page_no = 1
    while True:
        url = f"{state_url}?page={page_no}"
        soup = get_soup(session, url)
        page_rows = collect_district_rows_from_page(soup)
        added = 0
        for r in page_rows:
            if r["district"] not in seen:
                seen.add(r["district"]); all_rows.append(r); added += 1
        log(f"    districts page {page_no}: +{added}")
        if len(page_rows) < PAGE_SIZE or not page_rows: break
        page_no += 1; time.sleep(0.1)
    return all_rows

# ---------- using Playwright: child pages ----------
ROW_TITLE_JS = (
    "div.search-content .search-row .search-title, "
    "div.search-content .search-row.module .search-title, "
    "div.search-content .module.search-row .search-title, "
    "div.search-content .search-result-row .search-title"
)

def dom_row_count(page) -> int:
    try:
        return page.eval_on_selector_all(ROW_TITLE_JS, "els => els.length")
    except Exception:
        return 0

def child_expected(page) -> int | None:
    try:
        txt = page.locator("div.search-meta").first.inner_text(timeout=1500)
        m = re.search(r"(\d+)", txt or "")
        return int(m.group(1)) if m else None
    except Exception:
        return None

def child_page_links(page) -> list[str]:
    try:
        links = page.eval_on_selector_all(
            "ul.pagination li a[href]",
            "els => els.map(e => ({href: e.href, txt: (e.textContent||'').trim()}))"
        )
        hrefs, seen = [], set()
        for it in links:
            if not it["txt"].isdigit(): continue
            if it["href"] in seen: continue
            seen.add(it["href"]); hrefs.append(it["href"])
        return hrefs
    except Exception:
        return []

def child_names_from_dom(page) -> list[str]:
    names = page.eval_on_selector_all(ROW_TITLE_JS, "els => els.map(e => e.textContent.trim()).filter(Boolean)")
    if not names:
        names = page.eval_on_selector_all("div.search-content ul>li", "els => els.map(e => e.textContent.trim()).filter(Boolean)")
    out, seen = [], set()
    for n in names:
        if not n or n.lower().startswith("source:"): continue
        key = re.sub(r"\s+", " ", n.strip().lower())
        if key in seen: continue
        seen.add(key); out.append(n.strip())
    return out

def wait_until_reaches_banner(page, expected: int | None, max_loops=200, pause_s=0.4):
    last = -1; stagnation = 0
    for _ in range(max_loops):
        count = dom_row_count(page)
        if expected and count >= expected: return
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause_s)
        page.evaluate("window.scrollBy(0, -300)")
        time.sleep(0.15)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        try:
            page.wait_for_timeout(int(pause_s * 1000))
        except TimeoutError:
            pass
        new_count = dom_row_count(page)
        if new_count == last:
            stagnation += 1
            if stagnation >= 5: return
        else:
            stagnation = 0
        last = new_count

def collect_child_list(page, url: str, label: str) -> list[str]:
    if not url: return []
    names, seen = [], set()
    page.goto(url, wait_until="domcontentloaded")
    expected = child_expected(page)
    wait_until_reaches_banner(page, expected, max_loops=240, pause_s=0.45)
    for n in child_names_from_dom(page):
        key = re.sub(r"\s+", " ", n.lower())
        if key not in seen:
            seen.add(key); names.append(n)
    links = child_page_links(page)
    if links:
        if url not in links:
            links = [url] + [h for h in links if h != url]
        for pno, href in enumerate(links[1:], start=2):
            page.goto(href, wait_until="domcontentloaded")
            exp_p = child_expected(page)
            wait_until_reaches_banner(page, exp_p or expected, max_loops=200, pause_s=0.45)
            before = len(names)
            for n in child_names_from_dom(page):
                key = re.sub(r"\s+", " ", n.lower())
                if key not in seen:
                    seen.add(key); names.append(n)
            log(f"      {label} page {pno}: +{len(names)-before}")
    if expected is not None:
        if len(names) == expected:
            log(f"      [{label}] links found: {len(names)} (matches banner {expected})")
        else:
            log(f"      [WARN] {label.capitalize()} mismatch: expected {expected}, got {len(names)}")
    return names

# ---------- performing main ----------
def main():
    log(f"[IGOD hybrid DOM] Writing: {SUB_CSV} & {BLK_CSV}")
    write_headers_once()
    done = load_done()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) IGOD/Playwright")
        page = ctx.new_page()
        s = requests.Session()

        states = get_states(s)
        sub_f = open(SUB_CSV, "a", newline="", encoding="utf-8"); sub_w = csv.writer(sub_f)
        blk_f = open(BLK_CSV, "a", newline="", encoding="utf-8"); blk_w = csv.writer(blk_f)

        try:
            for state, surl in states:
                if state in done: continue
                log(f"== {state} ==")

                districts = get_all_districts_for_state(s, surl)
                written_sub, written_blk = set(), set()
                total_subs_found, total_blks_found = 0, 0
                total_subs_written, total_blks_written = 0, 0

                for d in districts:
                    subs = collect_child_list(page, d["sub"], "subdistrict") if d["sub"] else []
                    blks = collect_child_list(page, d["block"], "block") if d["block"] else []

                    total_subs_found += len(subs)
                    total_blks_found += len(blks)

                    # we write one row even if empty entry (i.e., no subdistrict / block) 
                    if not subs:
                        sub_w.writerow([state, d["district"], ""]); total_subs_written += 1
                    else:
                        for sd in subs:
                            sub_w.writerow([state, d["district"], sd]); total_subs_written += 1
                    if not blks:
                        blk_w.writerow([state, d["district"], ""]); total_blks_written += 1
                    else:
                        for b in blks:
                            blk_w.writerow([state, d["district"], b]); total_blks_written += 1

                    written_sub.add(d["district"])
                    written_blk.add(d["district"])

                sub_f.flush(); blk_f.flush()

                # Verifying if all districts (subdistricts and blocks) are written 
                scraped_districts = {d["district"] for d in districts}
                missing_sub = scraped_districts - written_sub
                missing_blk = scraped_districts - written_blk
                if missing_sub:
                    log(f"[WARN] Missing in subdistricts.csv: {', '.join(sorted(missing_sub))}")
                if missing_blk:
                    log(f"[WARN] Missing in blocks.csv: {', '.join(sorted(missing_blk))}")

                log(f"   -> subdistricts found: {total_subs_found}, written: {total_subs_written}")
                log(f"   -> blocks found: {total_blks_found}, written: {total_blks_written}")

                mark_done(state)
                log(f"   -> finished {state} ({len(scraped_districts)} districts)\n")
        finally:
            sub_f.close(); blk_f.close()
            ctx.close(); browser.close()

if __name__ == "__main__":
    main()