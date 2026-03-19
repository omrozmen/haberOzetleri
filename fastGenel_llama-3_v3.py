"""
`habericerikleri` klasöründeki tüm haber içeriklerini Türkçe ve hızlı biçimde özetleyen tek dosyalı araç.

Konfigürasyonu değiştirmek için dosyanın başındaki `get_run_config()` fonksiyonunu düzenlemeniz yeterli.
Komutu herhangi bir argüman vermeden `python fastGenel_llama-3.py` şeklinde çalıştırabilirsiniz.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List
from urllib import error, request
import time


DEFAULT_MODEL = "llama3:8b-instruct-q4_0"
DEFAULT_ENDPOINT = "http://localhost:11434/api/generate"


def get_run_config() -> Dict:
    """
    Öntanımlı değerleri buradan değiştirin.
    """
    return {
        "input_dir": Path("habericerikleri"),
        "output_dir": Path("haberOzetleri"),
        "title_dir": Path("haberBasliklari"),
        "model": DEFAULT_MODEL,
        "endpoint": DEFAULT_ENDPOINT,
        "workers": 4,
        "max_chars": 1400,
        "max_tokens": 150,
        "temperature": 0.25,
        "top_p": 0.9,
        "timeout": 90,
    }


def _normalize_content(raw) -> str:
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, list):
        parts = []
        for block in raw:
            if isinstance(block, str):
                text = block.strip()
            elif isinstance(block, dict):
                text = str(block.get("text") or block.get("content") or "").strip()
            else:
                text = ""
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip()
    if isinstance(raw, dict):
        return str(raw.get("text") or raw.get("content") or "").strip()
    return ""


def _trim_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    last_period = trimmed.rfind(".")
    if last_period > max_chars * 0.6:
        trimmed = trimmed[: last_period + 1]
    return trimmed.strip() + " …(metin kısaltıldı)"


def _build_prompt(body: str, title: str | None) -> str:
    talimat = (
        "Deneyimli bir haber editörüsün. "
        "Metni önce zihninde analiz edip ana tema, kritik aktörler, önemli veriler ve sonuçları belirle. "
        "Metindeki tüm gelişmeleri sebep-sonuç ilişkisi içinde kavradıktan sonra 2 ila 3 cümlelik tek paragrafta, haberin ana mesajını özetleyen kısa ve öz bir özet yaz. "
        "Çıktı dili kesinlikle Türkçe olsun ve cümleler arasında kopukluk olmasın. "
        "Kişi/kurum adları, kritik olaylar ve sonuç cümlesi mutlaka yer alsın; konunun bütününü anlamsal olarak kapsadığından emin ol. "
        "Ne-nerede-kim gibi başlıkları sıralama; olayların ana mesajını anlamsal bağlamını koruyarak aktar. "
        "Madde işareti, numaralı liste veya İngilizce ifade kullanma, kendinden bahsetme. "
        "Cevabı herhangi bir açıklama, giriş cümlesi veya alıntı olmadan doğrudan özet paragrafıyla ver ve tırnak işareti kullanma."
    )
    if title:
        return f"{talimat}\n\nBaşlık: {title.strip()}\nMetin:\n{body.strip()}\n\nÖzet:"
    return f"{talimat}\n\nMetin:\n{body.strip()}\n\nÖzet:"


def _summarize_with_llama(
    body: str,
    title: str | None,
    *,
    model: str,
    endpoint: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    timeout: int,
) -> str:
    payload = {
        "model": model,
        "prompt": _build_prompt(body, title),
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            summary = json.loads(raw).get("response", "").strip()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Ollama HTTP hatası: {exc.code} - {detail[:200]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Ollama bağlantı hatası: {exc.reason}") from exc
    if not summary:
        raise RuntimeError("LLM boş özet döndürdü.")
    return summary


def _dynamic_token_limit(text: str, base_max_tokens: int) -> int:
    """Metin uzunluğuna göre özet uzunluğunu sınırlı şekilde ayarla."""
    extra = max(0, len(text) - 700) // 10  # daha sıkı artış
    limit = base_max_tokens + extra
    return min(limit, int(base_max_tokens * 1.8))  # maksimum ~1.8 kat


def _load_news(path: Path, max_chars: int) -> List[Dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        iterable = raw.items()
    elif isinstance(raw, list):
        iterable = [(entry.get("title") or f"Haber {idx+1}", entry) for idx, entry in enumerate(raw)]
    else:
        raise ValueError("JSON beklenen biçimde değil.")

    news: List[Dict] = []
    for title, payload in iterable:
        if not isinstance(payload, dict):
            continue
        full_text = _normalize_content(payload.get("content") or payload.get("metin") or payload.get("text"))
        if not full_text:
            continue
        news.append(
            {
                "title": title,
                "url": payload.get("url"),
                "text": _trim_text(full_text, max_chars),
            }
        )
    if not news:
        raise ValueError("Geçerli haber kaydı bulunamadı.")
    return news


def _load_existing_output(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    normalized: Dict[str, Dict] = {}
    for title, payload in data.items():
        if not isinstance(payload, dict):
            continue
        normalized[title] = {
            "url": payload.get("url"),
            "summary": payload.get("summary", ""),
        }
    return normalized


def _prepare_targets(news_items: List[Dict], output_data: Dict[str, Dict]) -> List[Dict]:
    pending: List[Dict] = []
    for idx, item in enumerate(news_items, start=1):
        title = (item.get("title") or "").strip()
        if not title:
            title = f"Haber #{idx}"

        existing = output_data.get(title, {})
        merged = {
            "url": item.get("url") or existing.get("url"),
            "summary": existing.get("summary", "") or "",
        }
        output_data[title] = merged

        if merged["summary"].strip():
            continue

        pending.append({"title": title, "text": item["text"]})

    return pending


def _write_output(data: Dict[str, Dict], output_path: Path) -> None:
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_title_order(title_dir: Path, input_path: Path) -> List[str]:
    stem = input_path.stem
    candidate_names = [
        title_dir / f"{stem}_basliklari.json",
        title_dir / f"{stem.lower()}_basliklari.json",
        title_dir / f"{stem.capitalize()}_basliklari.json",
    ]
    for candidate in candidate_names:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return [title for title in data.values() if isinstance(title, str) and title.strip()]
            except json.JSONDecodeError:
                pass
    return []


def _order_news_by_titles(news_items: List[Dict], title_order: List[str]) -> List[Dict]:
    if not title_order:
        return news_items
    map_items = {item.get("title"): item for item in news_items}
    ordered = [map_items[title] for title in title_order if title in map_items]
    return ordered


def _apply_title_order(output_data: Dict[str, Dict], title_order: List[str]) -> Dict[str, Dict]:
    if not title_order:
        return output_data
    ordered: Dict[str, Dict] = {}
    for title in title_order:
        if title in output_data:
            ordered[title] = output_data[title]
    return ordered


def _collect_input_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"'{directory}' dizini bulunamadı.")
    if not directory.is_dir():
        raise NotADirectoryError(f"'{directory}' bir dizin değil.")
    files = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".json"
    )
    if not files:
        raise FileNotFoundError(f"'{directory}' dizininde özetlenecek JSON dosyası bulunamadı.")
    return files


def _process_single_file(input_path: Path, output_path: Path, cfg: Dict) -> int:
    title_order = _load_title_order(cfg["title_dir"], input_path)
    news_items = _order_news_by_titles(_load_news(input_path, cfg["max_chars"]), title_order)
    output_data = _load_existing_output(output_path)
    pending_targets = _prepare_targets(news_items, output_data)
    summarized_targets = summarize_news(
        pending_targets,
        workers=cfg["workers"],
        model=cfg["model"],
        endpoint=cfg["endpoint"],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        top_p=cfg["top_p"],
        timeout=cfg["timeout"],
    )
    for item in summarized_targets:
        title = item["title"]
        output_data.setdefault(title, {"url": None, "summary": ""})
        output_data[title]["summary"] = item.get("summary", "").strip()
    ordered_output = _apply_title_order(output_data, title_order)
    _write_output(ordered_output, output_path)
    return len(summarized_targets)


def summarize_news(
    items: List[Dict],
    *,
    workers: int,
    model: str,
    endpoint: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    timeout: int,
) -> List[Dict]:
    if not items:
        print("Özetlenecek yeni haber bulunamadı.")
        return []
    if workers < 1:
        workers = 1
    pending: Dict = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for idx, item in enumerate(items):
            token_limit = _dynamic_token_limit(item["text"], max_tokens)
            future = pool.submit(
                _summarize_with_llama,
                item["text"],
                item.get("title"),
                model=model,
                endpoint=endpoint,
                max_tokens=token_limit,
                temperature=temperature,
                top_p=top_p,
                timeout=timeout,
            )
            pending[future] = idx
        for done, future in enumerate(as_completed(pending), start=1):
            idx = pending[future]
            items[idx]["summary"] = future.result()
            print(f"[{done}/{len(pending)}] '{items[idx]['title']}' özetlendi.")
    return items


def main() -> None:
    cfg = get_run_config()
    input_dir = Path(cfg["input_dir"])
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    input_files = _collect_input_files(input_dir)
    start_time = time.time()
    processed_files = 0
    total_new_summaries = 0
    failures: List[str] = []

    for input_path in input_files:
        output_path = output_dir / input_path.name
        print(f"➡️  '{input_path.name}' dosyası işleniyor...")
        try:
            new_summaries = _process_single_file(input_path, output_path, cfg)
            processed_files += 1
            total_new_summaries += new_summaries
            if new_summaries:
                print(f"✅  '{input_path.name}' için {new_summaries} yeni özet kaydedildi.")
            else:
                print(f"ℹ️  '{input_path.name}' için yeni özet gerekmiyor, dosya güncel.")
        except Exception as exc:  # pragma: no cover - çalışma zamanı raporu
            failures.append(f"{input_path.name}: {exc}")
            print(f"❌  '{input_path.name}' işlenirken hata oluştu: {exc}")

    elapsed = time.time() - start_time
    print(
        f"\nToplam {processed_files} dosya işlendi ve {total_new_summaries} yeni özet üretildi."
    )
    print(f"⏱️  Toplam süre: {elapsed:.2f} saniye")
    if total_new_summaries:
        avg_time = elapsed / total_new_summaries
        print(f"⏱️  Ortalama süre (özet başına): {avg_time:.2f} saniye")
    if failures:
        print("Hata alınan dosyalar:")
        for item in failures:
            print(f" - {item}")
        raise SystemExit(1)
    print(f"Özetler '{output_dir}' klasörüne kaydedildi.")


if __name__ == "__main__":
    main()

