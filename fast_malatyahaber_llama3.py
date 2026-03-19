"""
Malatyahaber içeriklerini Türkçe ve hızlı biçimde özetleyen tek dosyalı araç.

Konfigürasyonu değiştirmek için dosyanın başındaki `get_run_config()` fonksiyonunu düzenlemeniz yeterli.
Komutu herhangi bir argüman vermeden `python fast_malatyahaber_llama3.py` şeklinde çalıştırabilirsiniz.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List
from urllib import error, request


DEFAULT_MODEL = "llama3:8b-instruct-q4_0"
DEFAULT_ENDPOINT = "http://localhost:11434/api/generate"


def get_run_config() -> Dict:
    """
    Öntanımlı değerleri buradan değiştirin.
    """
    return {
        "input_path": Path("new_contents_malatyahaber.json"),
        "output_path": Path("malatyahaber_llama3_fast.json"),
        "model": DEFAULT_MODEL,
        "endpoint": DEFAULT_ENDPOINT,
        "workers": 4,
        "max_chars": 2400,
        "max_tokens": 280,
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
        "Ardından 4 ila 6 cümlelik tek paragrafta, giriş-gelişme-sonuç ritmine sahip akıcı bir özet yaz. "
        "Çıktı dili kesinlikle Türkçe olsun ve cümleler arasında kopukluk olmasın. "
        "Kişi/kurum adları, tarih-sayı bilgilerinin yanı sıra örnekler ve çıkarımların vurgulandığından emin ol. "
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
    """Metin uzunluğuna göre daha uzun özetlere izin ver."""
    extra = max(0, len(text) - 600) // 4  # daha uzun metinler için daha geniş artış
    limit = base_max_tokens + extra
    return min(limit, base_max_tokens * 4)


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
    input_path = Path(cfg["input_path"])
    output_path = Path(cfg["output_path"])

    news_items = _load_news(input_path, cfg["max_chars"])
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

    _write_output(output_data, output_path)
    print(f"✅ Özetler '{output_path}' dosyasına kaydedildi.")


if __name__ == "__main__":
    main()

