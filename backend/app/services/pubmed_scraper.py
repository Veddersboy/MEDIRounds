"""
PubMed Central (PMC) article scraper and cleaner service.
Fetches full-text XML from NCBI EFetch and PMC Open Access S3 fallback,
extracts structured text, and writes JSON files.
"""

import asyncio
import json
import os
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_S3_URL = "https://pmc-oa-opendata.s3.amazonaws.com"
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_DIR, "output", "pubmed")
THIN_BODY_CHAR_THRESHOLD = 300
XML_PARSER = "lxml-xml"

RETRY_429_ATTEMPTS = 3
RETRY_429_BACKOFF_SECONDS = 2.0
PMCID_BLOB_RE = re.compile(r"PMC\d+", re.IGNORECASE)
S3_KEY_RE = re.compile(r"<Key>(.*?)</Key>")
SPLIT_WORD_RE = re.compile(r"(?<=[a-z])- (?=[a-z])")
HYPHEN_SPACE_RE = re.compile(r"(?<=\w)- (?=\w)")


def normalize_pmcid(raw: str) -> str:
    raw = raw.strip().upper()
    if not raw:
        raise ValueError("empty PMCID")
    if not raw.startswith("PMC"):
        raw = "PMC" + raw
    digits = raw[3:]
    if not digits.isdigit():
        raise ValueError(f"'{raw}' doesn't look like a PMCID (expected 'PMC' + digits)")
    return raw


def extract_all_pmcids(text: str) -> list[str]:
    matches = PMCID_BLOB_RE.findall(text)
    if matches:
        return [normalize_pmcid(m) for m in matches]

    ids: list[str] = []
    for token in text.replace(",", " ").split():
        try:
            ids.append(normalize_pmcid(token))
        except ValueError:
            continue
    return ids


def text_or_none(tag: Any) -> str | None:
    return tag.get_text(strip=True) if tag else None


def existing_json_path(pmcid: str, output_dir: str) -> str | None:
    path = os.path.join(output_dir, f"{pmcid}.json")
    return path if os.path.isfile(path) else None


def make_unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def fetch_pmc_xml(
    pmcid: str,
    api_key: str | None = None,
    email: str | None = None,
    tool: str = "medirounds-app",
) -> str:
    params: dict[str, str] = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml",
        "rettype": "full",
        "tool": tool,
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    for attempt in range(RETRY_429_ATTEMPTS + 1):
        resp = requests.get(EFETCH_URL, params=params, timeout=30)
        if resp.status_code == 429 and attempt < RETRY_429_ATTEMPTS:
            wait = float(resp.headers.get("Retry-After", RETRY_429_BACKOFF_SECONDS))
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.text
    return ""


def latest_s3_files(pmcid: str) -> dict[str, str]:
    resp = requests.get(
        PMC_S3_URL + "/",
        params={"list-type": "2", "prefix": f"{pmcid}."},
        timeout=30,
    )
    resp.raise_for_status()

    by_version: dict[int, list[tuple[str, str]]] = {}
    for key in S3_KEY_RE.findall(resp.text):
        folder, _, filename = key.partition("/")
        version = folder.rpartition(".")[2]
        if version.isdigit():
            by_version.setdefault(int(version), []).append((key, filename))
    if not by_version:
        return {}

    latest = by_version[max(by_version)]
    return {
        os.path.splitext(filename)[1].lstrip("."): f"{PMC_S3_URL}/{key}"
        for key, filename in latest
        if filename.startswith(f"{pmcid}.")
    }


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def clean_s3_text(txt: str, abstract: str | None = None) -> str:
    lines = txt.splitlines()
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip("\x9f \t")
        if stripped and set(stripped) == {"="}:
            start = i + 1
    text = "\n".join(lines[start:]).replace("\x9f", "").strip()

    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    abstract_key = _alnum(abstract or "")
    while blocks and abstract_key and _alnum(blocks[0]) in abstract_key:
        blocks.pop(0)

    text = "\n\n".join(blocks)
    text = SPLIT_WORD_RE.sub("", text)
    return HYPHEN_SPACE_RE.sub("-", text)


def add_pdf_text_fallback(data: dict[str, Any]) -> dict[str, Any]:
    data["full_text_source"] = "xml" if data["has_full_text"] else None
    data["pdf_url"] = None
    data["pdf_text"] = None
    if data["has_full_text"]:
        return data

    try:
        files = latest_s3_files(data["pmcid"])
        data["pdf_url"] = files.get("pdf")
        if "txt" in files:
            resp = requests.get(files["txt"], timeout=60)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            text = clean_s3_text(resp.text, abstract=data.get("abstract"))
            if text:
                data["pdf_text"] = text
                data["full_text_source"] = "pdf"
    except requests.RequestException:
        pass
    return data


def parse_authors(article_meta: Any) -> list[dict[str, Any]]:
    authors = []
    for contrib in article_meta.find_all("contrib", {"contrib-type": "author"}):
        name_tag = contrib.find("name")
        if name_tag:
            surname = text_or_none(name_tag.find("surname"))
            given = text_or_none(name_tag.find("given-names"))
            full_name = " ".join(p for p in [given, surname] if p)
        else:
            full_name = text_or_none(contrib.find("collab"))
        aff_ids = [x.get("rid") for x in contrib.find_all("xref", {"ref-type": "aff"})]
        authors.append({"name": full_name, "affiliation_ids": aff_ids})
    return authors


def parse_affiliations(article_meta: Any) -> dict[str, str]:
    return {
        aff.get("id"): aff.get_text(" ", strip=True)
        for aff in article_meta.find_all("aff")
        if aff.get("id")
    }


def parse_pub_date(article_meta: Any) -> str | None:
    pub_date = article_meta.find("pub-date")
    if not pub_date:
        return None
    parts = [text_or_none(pub_date.find(tag)) for tag in ("year", "month", "day")]
    parts = [p for p in parts if p]
    return "-".join(parts) if parts else None


def parse_section(sec: Any) -> dict[str, Any]:
    return {
        "heading": text_or_none(sec.find("title", recursive=False)),
        "paragraphs": [p.get_text(" ", strip=True) for p in sec.find_all("p", recursive=False)],
        "subsections": [parse_section(s) for s in sec.find_all("sec", recursive=False)],
    }


def parse_body(body: Any) -> list[dict[str, Any]]:
    if not body:
        return []
    sections = []
    direct_paragraphs = [p.get_text(" ", strip=True) for p in body.find_all("p", recursive=False)]
    if direct_paragraphs:
        sections.append({"heading": None, "paragraphs": direct_paragraphs, "subsections": []})
    sections.extend(parse_section(sec) for sec in body.find_all("sec", recursive=False))
    return sections


def parse_self_uri_links(article_meta: Any, pmcid: str | None) -> list[dict[str, Any]]:
    base = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else None
    links = []
    for tag in article_meta.find_all("self-uri"):
        href = tag.get("xlink:href")
        if not href:
            continue
        if base and not href.startswith(("http://", "https://")):
            href = base + href.lstrip("/")
        links.append({
            "content_type": tag.get("content-type"),
            "href": href,
            "text": text_or_none(tag),
        })
    return links


def parse_body_ext_links(body: Any) -> list[dict[str, Any]]:
    if not body:
        return []
    return [
        {"href": tag.get("xlink:href"), "text": text_or_none(tag)}
        for tag in body.find_all("ext-link")
        if tag.get("xlink:href")
    ]


def body_char_count(sections: list[dict[str, Any]]) -> int:
    total = 0
    for sec in sections:
        total += sum(len(p) for p in sec.get("paragraphs", []))
        total += body_char_count(sec.get("subsections", []))
    return total


def parse_references(article: Any) -> list[dict[str, Any]]:
    refs = []
    ref_list = article.find("ref-list")
    if not ref_list:
        return refs
    for ref in ref_list.find_all("ref"):
        citation = ref.find("element-citation") or ref.find("mixed-citation")
        if not citation:
            continue
        refs.append({
            "id": ref.get("id"),
            "authors": [n.get_text(" ", strip=True) for n in citation.find_all("name")],
            "title": text_or_none(citation.find("article-title")),
            "source": text_or_none(citation.find("source")),
            "year": text_or_none(citation.find("year")),
            "doi": text_or_none(citation.find("pub-id", {"pub-id-type": "doi"})),
        })
    return refs


def parse_article(xml_text: str, requested_pmcid: str | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(xml_text, XML_PARSER)

    error_tag = soup.find(lambda t: t.name and t.name.lower() == "error")
    if error_tag is not None:
        raise ValueError(f"NCBI returned an error for {requested_pmcid}: {error_tag.get_text(strip=True)}")

    article = soup.find("article")
    if article is None:
        raise ValueError(
            f"No <article> full text returned for {requested_pmcid}. It may not be part of "
            "the PMC Open Access subset, so EFetch only returns citation metadata, not body text."
        )

    article_meta = article.find("article-meta")
    journal_meta = article.find("journal-meta")

    pmcid = pmid = doi = None
    for aid in article_meta.find_all("article-id"):
        id_type = aid.get("pub-id-type")
        if id_type == "pmc":
            pmcid = normalize_pmcid(aid.get_text(strip=True))
        elif id_type == "pmid":
            pmid = aid.get_text(strip=True)
        elif id_type == "doi":
            doi = aid.get_text(strip=True)

    affiliations = parse_affiliations(article_meta)
    authors = parse_authors(article_meta)
    for author in authors:
        author["affiliations"] = [affiliations[i] for i in author["affiliation_ids"] if i in affiliations]

    body_tag = article.find("body")
    body_sections = parse_body(body_tag)
    alternate_renditions = parse_self_uri_links(article_meta, pmcid or requested_pmcid)
    body_external_links = parse_body_ext_links(body_tag)

    is_stub_body = (
        bool(body_sections)
        and body_char_count(body_sections) < THIN_BODY_CHAR_THRESHOLD
        and bool(alternate_renditions or body_external_links)
    )

    return {
        "pmcid": pmcid or requested_pmcid,
        "pmid": pmid,
        "doi": doi,
        "title": text_or_none(article_meta.find("article-title")),
        "journal": text_or_none(journal_meta.find("journal-title")) if journal_meta else None,
        "issn": text_or_none(journal_meta.find("issn")) if journal_meta else None,
        "authors": authors,
        "publication_date": parse_pub_date(article_meta),
        "keywords": [k.get_text(strip=True) for k in article_meta.find_all("kwd")],
        "abstract": text_or_none(article_meta.find("abstract")),
        "body": body_sections,
        "has_full_text": bool(body_sections) and not is_stub_body,
        "is_stub_body": is_stub_body,
        "alternate_renditions": alternate_renditions,
        "body_external_links": body_external_links,
        "references": parse_references(article),
    }


def fetch_article(pmcid: str, api_key: str | None = None, email: str | None = None) -> dict[str, Any]:
    xml_text = fetch_pmc_xml(pmcid, api_key=api_key, email=email)
    data = parse_article(xml_text, requested_pmcid=pmcid)
    return add_pdf_text_fallback(data)


def scrape_articles_sync(
    pmcids: list[str],
    output_dir: str,
    overwrite: bool = False,
    api_key: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    target_dir = os.path.abspath(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    os.makedirs(target_dir, exist_ok=True)

    results: dict[str, Any] = {
        "output_dir": target_dir,
        "total": len(pmcids),
        "saved": [],
        "skipped": [],
        "errors": [],
    }

    rps = 10 if api_key else 3
    interval = 1.0 / rps

    for i, raw in enumerate(pmcids):
        try:
            norm_id = normalize_pmcid(raw)
        except Exception as e:
            results["errors"].append({"id": raw, "error": str(e)})
            continue

        out_path = os.path.join(target_dir, f"{norm_id}.json")
        if os.path.isfile(out_path) and not overwrite:
            results["skipped"].append({"id": norm_id, "path": out_path})
            continue

        try:
            data = fetch_article(norm_id, api_key=api_key, email=email)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            results["saved"].append({
                "id": norm_id,
                "path": out_path,
                "title": data.get("title") or norm_id,
                "data": data,
            })
        except Exception as e:
            results["errors"].append({"id": norm_id, "error": str(e)})

        if i < len(pmcids) - 1:
            time.sleep(interval)

    return results


async def scrape_articles(
    pmcids: list[str],
    output_dir: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    api_key = os.environ.get("NCBI_API_KEY")
    email = os.environ.get("NCBI_EMAIL")
    return await asyncio.to_thread(
        scrape_articles_sync,
        pmcids,
        output_dir,
        overwrite,
        api_key,
        email,
    )
