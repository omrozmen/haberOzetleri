import requests
from bs4 import BeautifulSoup
import json
import os
import logging
import schedule
import time



# Logging ayarları
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Siteye özgü ayarları tutan bir yapı
sites_config = [
    {
        "name": "Ensonhaber",
        "base_url": "https://www.ensonhaber.com/",
        "main_div_id": None,
        "main_div_class": "swiper main-slider",
        "output_file": "combined_news_ensonhaber.json",
        "content_file": "new_contents_ensonhaber.json",
        "tags": ["blockquote", "p", "h1", "h2","strong"]
    },
    {
        "name": "Malatyahaber",
        "base_url": "https://www.malatyahaber.com/",
        "main_div_id": "manset-alani",
        "main_div_class": None,
        "output_file": "combined_news_malatyahaber.json",
        "content_file": "new_contents_malatyahaber.json",
        "tags": ["p", "h1", "h2","blockquote","strong"]
    },
        {
        "name": "Haberler",
        "base_url": "https://www.haberler.com/",
        "main_div_id": "sliderWrapper",
        "main_div_class": None,
        "output_file": "combined_news_haberler.json",
        "content_file": "new_contents_haberler.json",
        "tags": ["p", "h1", "h2","blockquote","strong"]
    },
        {
        "name": "internethaber",
        "base_url": "https://www.internethaber.com/",
        "main_div_id": None,
        "main_div_class": "swiper-wrapper",
        "output_file": "combined_news_internethaber.json",
        "content_file": "new_contents_internethaber.json",
        "tags": ["blockquote", "p", "h1", "h2","h3"]
    },
     {
        "name": "İnternetSpor",
        "base_url": "https://www.internetspor.com/",
        "main_div_id": None,
        "main_div_class": "headline",
        "output_file": "combined_news_internetSpor.json",
        "content_file": "new_contents_internetSpor.json",
        "tags": ["p", "h1", "h2","blockquote"]
    },
        {
        "name": "MalatyaGuncel",
        "base_url": "https://www.malatyaguncel.com/",
        "main_div_id": None,
        "main_div_class": "owl-stage",
        "output_file": "combined_news_MalatyaGuncel.json",
        "content_file": "new_contents_MalatyaGuncel.json",
        "tags": ["p", "h1", "h2","blockquote"]
    }
    
]

def get_combined_text_in_order(news_url, tags):
    """
    Haberin metnini belirtilen etiketlere göre, aynı türden etiketleri birleştirerek akış sırasına göre alır.
    """
    try:
        response = requests.get(news_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        content = []
        current_tag = None
        current_text = ""

        for element in soup.find_all(tags):
            if current_tag is None or element.name == current_tag:
                current_tag = element.name
                current_text += (element.get_text(strip=True) + " ")
            else:
                content.append({"tag": current_tag, "text": current_text.strip()})
                current_tag = element.name
                current_text = element.get_text(strip=True) + " "

        if current_text:
            content.append({"tag": current_tag, "text": current_text.strip()})

        return content
    except Exception as e:
        logging.error(f"Metin birleştirme sırasında hata: {e}")
        return []

def scrape_and_save_combined_text(config):
    """
    Belirtilen siteye ait ayarları kullanarak haberleri kazır ve kaydeder.
    Yeni başlıkları kaynak sırasına göre düzenler.
    """
    try:
        response = requests.get(config["base_url"])
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        # main_div = soup.find("div", id=config["main_div_id"])
        # "main_div_id" veya "main_div_class" değerlerinden hangisi None değilse onu kullan
        main_div = None
        if config.get("main_div_id"):
            main_div = soup.find("div", id=config["main_div_id"])
        elif config.get("main_div_class"):
            main_div = soup.find("div", class_=config["main_div_class"])
        
        if not main_div:
            logging.warning(f"{config['name']} için '{config['main_div_id']}' div'i bulunamadı!")
            return
        
        links = []
        titles = []
        for a_tag in main_div.find_all("a", href=True, title=True):
            href = a_tag['href']
            if not href.startswith("http"):
                href = config["base_url"].rstrip("/") + "/" + href.lstrip("/")
            links.append(href)
            titles.append(a_tag['title'])
        
        # Mevcut başlıkları yükle
        existing_titles = load_existing_titles(config["output_file"])
        all_news = {}
        new_contents = {}
        
        # Yeni başlıkları topla ve içerikleri hazırla
        for i, (link, title) in enumerate(zip(links, titles), 1):
            if title not in existing_titles.values():
                combined_content = get_combined_text_in_order(link, config["tags"])
                new_contents[title] = {
                    "url": link,
                    "content": combined_content
                }
        
        # Yeni ve mevcut başlıkları kaynak sırasına göre düzenle
        updated_titles = reorder_titles_by_source(titles, existing_titles)
        
        # Güncellenmiş başlıkları ve içerikleri kaydet
        save_titles_to_json(updated_titles, config["output_file"])
        
        if new_contents:
            save_to_json(config["content_file"], new_contents)
            logging.info(f"{config['name']} için yeni içerikler '{config['content_file']}' dosyasına kaydedildi.")
        else:
            logging.info(f"{config['name']} için yeni içerik bulunamadı.")
    
    except requests.RequestException as e:
        logging.error(f"{config['name']} için HTTP isteği sırasında hata oluştu: {e}")
    except Exception as e:
        logging.error(f"{config['name']} için scraper fonksiyonunda bir hata oluştu: {e}")

def reorder_titles_by_source(source_titles, existing_titles):
    """
    Kaynak sırasına göre mevcut başlıkları yeniden düzenler.
    """
    # Kaynak sırasındaki başlıkları mevcut başlıklarla birleştir
    combined_titles = source_titles + list(existing_titles.values())
    
    # Benzersiz başlıkları koruyarak sıralamayı düzenle
    unique_titles = []
    [unique_titles.append(title) for title in combined_titles if title not in unique_titles]
    
    # Yeni sıralamayı oluştur ve yeniden numaralandır
    reordered_titles = {str(i + 1): title for i, title in enumerate(unique_titles)}
    return reordered_titles


def load_existing_titles(json_file):
    """
    Mevcut başlıkların bulunduğu JSON dosyasını yükler.
    """
    try:
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Başlıkları yüklerken hata: {e}")
        return {}
        

def save_titles_to_json(titles, json_file):
    """
    Başlık listesini sıralı bir şekilde JSON dosyasına kaydeder.
    """
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(titles, f, ensure_ascii=False, indent=4)
        logging.info(f"Başlıklar '{json_file}' dosyasına kaydedildi.")
    except Exception as e:
        logging.error(f"Başlıkları kaydederken hata: {e}")

def save_to_json(json_file, data):
    """
    Veriyi JSON dosyasına ekler ya da yeni bir dosya oluşturur.
    """
    try:
        existing_data = {}
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)

        # Yeni verileri mevcut verilerin en başına ekleyerek günceller
        updated_data = {**data, **existing_data}
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
        logging.info(f"Veriler '{json_file}' dosyasına güncellenerek kaydedildi.")
    except Exception as e:
        logging.error(f"JSON dosyasına kaydederken hata: {e}")


if __name__ == "__main__":
    for site_config in sites_config:
        scrape_and_save_combined_text(site_config)


# def run_news():
#     # sites_config ve scrape_and_save_combined_text burada tanımlı olmalı
#     for site_config in sites_config:
#         scrape_and_save_combined_text(site_config)

# schedule.every(30).minutes.do(run_news)

# if __name__ == "__main__":
#     while True:
#         try:
#             schedule.run_pending()
#             time.sleep(1)  # CPU yükünü azaltmak için
#             print("Kazıyıcı çalışıyor...")
#         except Exception as e:
#             logging.error(f"Schedule döngüsü sırasında hata: {e}")

