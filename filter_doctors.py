import os
import glob
from io import BytesIO
from datetime import datetime

import pandas as pd
import requests
from openpyxl import load_workbook
from bs4 import BeautifulSoup


# -----------------------------
# Configuration (EDIT HERE)
# -----------------------------
# IMPORTANT: Do NOT hardcode secrets in the file if you plan to publish it.
# Use environment variables instead.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Locations you care about (must match the "Kraj" values in the Excel).
LOCATION_FILTER = [
    "1000 LJUBLJANA",
    "1230 DOMŽALE",
    "1260 LJUBLJANA - POLJE",
    "1290 GROSUPLJE",
    "4000 KRANJ",
]

# Which GP/clinic types you care about (must match "Naziv ZZZS dejavnosti").
SERVICE_FILTER = [
    "Splošna dejavnost - splošna ambulanta",
    "Amb. specializanta družinske medicine",
    "Splošna ambulanta - dodatno 0,5 DMS",
]

# Excel column value that indicates the doctor accepts new patients.
ACCEPTING_NEW_VALUE = "DA"


# ZZZS page that contains a link to the latest Excel file.
ZZZS_PAGE_URL = (
    "https://zavarovanec.zzzs.si/izbira-in-zamenjava-osebnega-zdravnika/"
    "seznami-zdravnikov/"
)

# This is the visible link text we look for on the ZZZS page.
LINK_TEXT_CONTAINS = "Število opredeljenih pri splošnih zdravnikih"


def get_latest_download_url() -> str:
    """
    Scrape the ZZZS page and extract the download link for the latest Excel file.

    If the page structure or link text changes, this is the first place to adjust.
    """
    r = requests.get(ZZZS_PAGE_URL, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    link = soup.find("a", string=lambda t: t and LINK_TEXT_CONTAINS in t)
    if not link:
        raise RuntimeError(
            "Could not find the relevant download link on the ZZZS page. "
            "The page layout or link text may have changed."
        )

    href = link.get("href", "")
    if not href:
        raise RuntimeError("Found link element, but it has no href attribute.")

    # Convert relative href to absolute URL
    return href if href.startswith("http") else requests.compat.urljoin(ZZZS_PAGE_URL, href)


def download_excel(url: str) -> BytesIO:
    """Download the Excel file into memory (BytesIO)."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return BytesIO(resp.content)


def read_source_date(excel_buf: BytesIO) -> str:
    """
    In your file, the source date is stored in cell B2.
    We read it using openpyxl (data_only=True) and return a string.
    """
    wb = load_workbook(excel_buf, data_only=True)
    sheet = wb.active

    raw = sheet["B2"].value
    if not raw:
        return "Unknown"

    # Some files store it as a string; some as something else. Normalize.
    return str(raw).strip()


def parse_excel_to_dataframe(excel_buf: BytesIO) -> pd.DataFrame:
    """
    Load the main table with pandas.

    header=3 means: the column names are on the 4th row of the sheet
    (0-based indexing).
    """
    # Reset buffer position before pandas reads it.
    excel_buf.seek(0)

    df = pd.read_excel(excel_buf, engine="openpyxl", header=3)
    df.columns = df.columns.str.strip()

    # Normalize relevant columns for safe comparisons.
    df["Kraj"] = df["Kraj"].astype(str).str.strip()
    df["Naziv ZZZS dejavnosti"] = df["Naziv ZZZS dejavnosti"].astype(str).str.strip()
    df["Zdravnik še sprejema zavarovane osebe"] = (
        df["Zdravnik še sprejema zavarovane osebe"].astype(str).str.strip()
    )

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply your location + service + accepting-new filters."""
    return df[
        df["Kraj"].isin(LOCATION_FILTER)
        & df["Naziv ZZZS dejavnosti"].isin(SERVICE_FILTER)
        & (df["Zdravnik še sprejema zavarovane osebe"] == ACCEPTING_NEW_VALUE)
    ]


def safe_iso_date_from_source(source_date: str) -> str:
    """
    Convert source date from 'DD.MM.YYYY' to 'YYYY-MM-DD'.
    If parsing fails, return 'unknown_date'.
    """
    try:
        parsed = datetime.strptime(source_date, "%d.%m.%Y")
        return parsed.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"⚠️ Could not parse source date '{source_date}': {e}")
        return "unknown_date"


def write_csv_with_header_comment(df: pd.DataFrame, output_path: str, source_date: str) -> None:
    """
    Save CSV and keep the 'Vir podatkov' line as a comment for traceability.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Vir podatkov: {source_date}\n")
        df.to_csv(f, index=False)


def make_comparable_id(df: pd.DataFrame) -> pd.Series:
    """
    Build a stable-ish identifier string for diffing day-to-day.

    NOTE: If columns change in the source file, update this function.
    """
    return (
        df["Priimek in ime zdravnika"].astype(str).str.strip()
        + " | "
        + df["Naziv izvajalca"].astype(str).str.strip()
        + " | "
        + df["Ulica"].astype(str).str.strip()
        + " | "
        + df["Kraj"].astype(str).str.strip()
    )


def build_change_summary(source_date: str) -> str:
    """
    Compare the newest CSV with the previous one (if it exists) and produce
    a human-readable summary.
    """
    all_files = sorted(glob.glob("filtered_doctors_*.csv"))

    # If we don't have at least 2 days of data, we can't diff.
    if len(all_files) < 2:
        return (
            f"📋 Spremembe v seznamu zdravnikov za {source_date}:\n"
            "Ni dovolj zgodovine za primerjavo (manjkata vsaj 2 CSV datoteki)."
        )

    prev_file = all_files[-2]
    today_file = all_files[-1]

    print(f"🔍 Comparing with previous file: {prev_file}")

    prev_df = pd.read_csv(prev_file, comment="#")
    today_df = pd.read_csv(today_file, comment="#")

    prev_ids = set(make_comparable_id(prev_df))
    today_ids = set(make_comparable_id(today_df))

    added = today_ids - prev_ids
    removed = prev_ids - today_ids

    lines = [f"📋 Spremembe v seznamu zdravnikov za {source_date}:"]

    if not added and not removed:
        lines.append("Ni sprememb")
        return "\n".join(lines)

    if added:
        lines.append(f"🟢 Dodani: {len(added)}")
        for a in sorted(added):
            lines.append(f"  + {a}")

    if removed:
        lines.append(f"🔴 Odstranjeni: {len(removed)}")
        for r in sorted(removed):
            lines.append(f"  - {r}")

    return "\n".join(lines)


def send_telegram_message(text: str) -> None:
    """
    Send a Telegram message if token/chat_id are configured.

    We intentionally do NOT use parse_mode here because:
    - your text contains characters (like '|') that can break Markdown parsing
    - plain text is more robust for a public project
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID).")
        print("Message that would have been sent:\n" + text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )

    if resp.status_code == 200:
        print("📬 Telegram notification sent.")
    else:
        print(f"⚠️ Failed to send Telegram message: {resp.status_code} {resp.text}")


def main():
    # 1) Find and download the latest Excel
    download_url = get_latest_download_url()
    print("✅ Using download URL:", download_url)
    excel_buf = download_excel(download_url)

    # 2) Read source date from B2
    source_date = read_source_date(excel_buf)

    # 3) Parse and filter
    df = parse_excel_to_dataframe(excel_buf)
    filtered = apply_filters(df)

    # 4) Save CSV with date in filename
    iso_date = safe_iso_date_from_source(source_date)
    output_path = f"filtered_doctors_{iso_date}.csv"
    write_csv_with_header_comment(filtered, output_path, source_date)

    print(f"\n✅ {len(filtered)} doctors matched. Source date: {source_date}. Saved to {output_path}.")

    # 5) Build change summary and notify
    summary = build_change_summary(source_date)
    send_telegram_message(summary)


if __name__ == "__main__":
    main()
