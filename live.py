import xml.etree.ElementTree as ET
import random
import uuid
import fetcher
import json
import os
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus

# Vercel Proxy Ayarları
MFPLINK = "https://etherium-iota.vercel.app"  # Kendi Vercel domaininiz
MFPPSW = "Milito22."

# Constants
REFERER = "forcedtoplay.xyz"
ORIGIN = "forcedtoplay.xyz"
PROXY = f"{MFPLINK}/api/proxy?url="
PROXY2 = f"&api_password={MFPPSW}"
HEADER = f"&h_user-agent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F133.0.0.0+Safari%2F537.36&h_referer=https%3A%2F%2F{REFERER}%2F&h_origin=https%3A%2F%2F{ORIGIN}"
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "itaevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"
SKYSTR = "help"
GUARCAL = "online"

# Logo önbellekleri
LOGO_CACHE = {}
LOCAL_LOGO_CACHE = []
LOCAL_LOGO_FILE = "guardacalcio_image_links.txt"

# Headers for requests
headers = {
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,ru;q=0.5",
    "Priority": "u=1, i",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "Sec-Ch-UA-Mobile": "?0",
    "Sec-Ch-UA-Platform": "Windows",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Storage-Access": "active",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

# Varsa eski çıktı dosyasını sil
if os.path.exists(M3U8_OUTPUT_FILE):
    os.remove(M3U8_OUTPUT_FILE)

def load_local_logos():
    """Yerel dosyadan logo bağlantılarını önbelleğe yükler."""
    if not LOCAL_LOGO_CACHE:
        try:
            with open(LOCAL_LOGO_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        LOCAL_LOGO_CACHE.append(line)
            print(f"Caricati {len(LOCAL_LOGO_CACHE)} loghi dal file locale: {LOCAL_LOGO_FILE}")
        except FileNotFoundError:
            print(f"File locale dei loghi non trovato: {LOCAL_LOGO_FILE}.")
        except Exception as e:
            print(f"Errore durante il caricamento del file locale dei loghi {LOCAL_LOGO_FILE}: {e}")

def get_dynamic_logo(event_name):
    """Etkinlik adına göre uygun logoyu arar veya varsayılanı döner."""
    teams_match = re.search(r':\s*([^:]+?)\s+vs\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)
    if not teams_match:
        teams_match = re.search(r'([^:]+?)\s+-\s+([^:]+?)(?:\s+[-|]|$)', event_name, re.IGNORECASE)

    if teams_match:
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        cache_key = f"{team1} vs {team2}"

        if cache_key in LOGO_CACHE:
            return LOGO_CACHE[cache_key]

        load_local_logos()
        if LOCAL_LOGO_CACHE:
            team1_lower = team1.lower()
            team2_lower = team2.lower()
            for logo_url in LOCAL_LOGO_CACHE:
                logo_url_lower = logo_url.lower()
                if team1_lower in logo_url_lower and team2_lower in logo_url_lower:
                    LOGO_CACHE[cache_key] = logo_url
                    return logo_url
                elif team1_lower in logo_url_lower or team2_lower in logo_url_lower:
                    LOGO_CACHE[cache_key] = logo_url
                    return logo_url

    return LOGO

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_stream_link(dlhd_id, event_name="", channel_name=""):
    """Kanal ID'si üzerinden akış bağlantısını oluşturur."""
    if channel_name and "Tennis Stream" in channel_name:
        return "https://dlhd.pk/watch.php?id=576"
    return f"https://dlhd.pk/watch.php?id={dlhd_id}"

def clean_group_title(sport_key):
    """Kategori başlığını temizler."""
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip()
    return clean_key.title() if clean_key else sport_key.strip()

def process_events():
    dadjson = loadJSON(DADDY_JSON_FILE)

    total_events = 0
    processed_channels = 0

    # M3U8 dosyasının başlığını yaz
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Etkinlikleri döngüye al
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                clean_sport_key = clean_group_title(sport_key)
                total_events += len(sport_events)

                for game in sport_events:
                    for channel in game.get("channels", []):
                        try:
                            # Tarih temizleme
                            clean_day = day.replace(" - Schedule Time UK GMT", "")
                            clean_day = clean_day.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
                            clean_day = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_day)

                            day_parts = clean_day.split()
                            day_num, month_name, year = None, None, None

                            if len(day_parts) >= 4:
                                if any(c.isalpha() for c in day_parts[1]):
                                    month_name, day_num = day_parts[1], day_parts[2]
                                else:
                                    day_num, month_name = day_parts[1], day_parts[2]
                                year = day_parts[3]
                            elif len(day_parts) == 3:
                                if day_parts[0].lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                                    day_num = day_parts[1]
                                    month_name = datetime.datetime.now(pytz.timezone('Europe/Rome')).strftime('%B')
                                    year = day_parts[2]
                                else:
                                    day_num, month_name, year = day_parts[0], day_parts[1], day_parts[2]
                            else:
                                now = datetime.datetime.now(pytz.timezone('Europe/Rome'))
                                day_num, month_name, year = now.strftime('%d'), now.strftime('%B'), now.strftime('%Y')

                            # Gün numarasını doğrula
                            day_num_digits = re.sub(r'[^0-9]', '', str(day_num)) if day_num else ""
                            day_num = day_num_digits if day_num_digits else datetime.datetime.now(pytz.timezone('Europe/Rome')).strftime('%d')

                            # Saat dönüşümü (UK -> CET/İtalya saati için +2 saat)
                            time_str = game.get("time", "00:00")
                            time_parts = time_str.split(":")
                            if len(time_parts) == 2:
                                hour = (int(time_parts[0]) + 2) % 24
                                time_str_cet = f"{hour:02d}:{time_parts[1]}"
                            else:
                                time_str_cet = time_str

                            month_map = {
                                "January": "01", "February": "02", "March": "03", "April": "04",
                                "May": "05", "June": "06", "July": "07", "August": "08",
                                "September": "09", "October": "10", "November": "11", "December": "12"
                            }
                            month_num = month_map.get(month_name, "01")

                            if len(str(day_num)) == 1:
                                day_num = f"0{day_num}"

                            year_short = str(year)[-2:]
                            formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                            # Kanal adı ve Etkinlik ayrıntıları
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channel_name_str = channel["channel_name"]
                                channelID = str(channel.get("channel_id", uuid.uuid4()))
                            else:
                                channel_name_str = str(channel)
                                channelID = str(uuid.uuid4())

                            event_details = game.get("event", "Sports Event")
                            event_name = event_details.split(":")[0].strip() if ":" in event_details else event_details.strip()

                            stream_url_dynamic = get_stream_link(channelID, event_details, channel_name_str)

                            if stream_url_dynamic:
                                with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                    tvg_name = f"{time_str_cet} {event_details} - {day_num}/{month_num}/{year_short}"
                                    event_logo = get_dynamic_logo(event_details)

                                    file.write(f'#EXTINF:-1 tvg-id="{event_name}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{clean_sport_key}", {channel_name_str}\n')
                                    file.write(f"{PROXY}{stream_url_dynamic}{PROXY2}\n\n")

                                processed_channels += 1

                        except Exception as e:
                            print(f"Hata oluştu (Kanal İşleme): {e}")
                            continue

        except KeyError as e:
            print(f"KeyError: {e}")

    print(f"\n=== Özet ===")
    print(f"Toplam İşlenen Etkinlik Sayısı: {total_events}")
    print(f"Eklenen Toplam Kanal Sayısı: {processed_channels}")
    print(f"===============\n")

    return processed_channels

def main():
    total_processed = process_events()
    print(f"M3U8 dosyası {total_processed} kanal ile başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()
