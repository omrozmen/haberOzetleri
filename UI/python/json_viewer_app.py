import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from flask import (
        Flask,
        abort,
        jsonify,
        render_template,
        request,
    )  # type: ignore[import]
except ModuleNotFoundError:
    Flask = None  # type: ignore
    abort = None  # type: ignore
    render_template = None  # type: ignore
    request = None  # type: ignore


BASE_DIR = Path(__file__).parent.parent.parent  # UI/python klasöründen proje kök dizinine çık

OZETLER_DIR = BASE_DIR / "haberOzetleri"
OZETLER_MISTRAL_DIR = BASE_DIR / "haberOzetleri_mistral"
ICERIKLER_DIR = BASE_DIR / "habericerikleri"
BASLIKLAR_DIR = BASE_DIR / "haberBasliklari"

MODEL_DIRECTORIES: Dict[str, Path] = {
    "llama": OZETLER_DIR,
    "mistral": OZETLER_MISTRAL_DIR,
}


def discover_news_sources(ozet_dir: Path = OZETLER_DIR) -> List[str]:
    """Belirtilen özet klasörü ve habericerikleri klasörlerindeki ortak dosya isimlerini bul."""
    ozet_files = set(
        p.stem for p in ozet_dir.glob("*.json") if p.is_file()
    )
    icerik_files = set(
        p.stem for p in ICERIKLER_DIR.glob("*.json") if p.is_file()
    )
    # Her iki klasörde de bulunan dosyalar
    common = sorted(ozet_files & icerik_files)
    return common


def resolve_model_directory(model_param: Optional[str]) -> Tuple[str, Path]:
    """İstenen modele göre özet klasörünü döndür."""
    model_key = (model_param or "llama").lower()
    directory = MODEL_DIRECTORIES.get(model_key)
    if directory is None:
        raise ValueError(f"Geçersiz model parametresi: {model_param}")
    return model_key, directory


def load_json_file(filepath: Path, preserve_order: bool = False) -> Any:
    """JSON dosyasını yükle. preserve_order=True ise sıralamayı korur."""
    if not filepath.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {filepath}")
    with filepath.open(encoding="utf-8") as f:
        if preserve_order:
            return json.load(f, object_pairs_hook=OrderedDict)
        return json.load(f)


def _extract_summary(payload: Any) -> Optional[str]:
    """JSON payload'dan özeti çıkar."""
    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, str):
            return summary
    elif isinstance(payload, str):
        return payload
    return None


def _extract_content(payload: Any) -> Optional[List[Dict[str, str]]]:
    """JSON payload'dan içerik bloklarını çıkar."""
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            return content
    return None


def _extract_url(payload: Any) -> Optional[str]:
    """JSON payload'dan URL'i çıkar."""
    if isinstance(payload, dict):
        url = payload.get("url")
        if isinstance(url, str):
            return url
    return None


def get_content_order(icerik_data: Any) -> List[str]:
    """İçerik dosyasındaki başlıkların sırasını al."""
    if not isinstance(icerik_data, (dict, OrderedDict)):
        return []
    
    # Dict veya OrderedDict'teki insertion order'ı koru
    return list(icerik_data.keys())


def load_news_data(source: str, ozet_dir: Path = OZETLER_DIR) -> Tuple[Dict[str, str], Dict[str, List[Dict[str, str]]], Dict[str, str], List[str]]:
    """
    Belirtilen kaynak için özet ve içerik dosyalarını yükle.
    Returns: (summary_map, content_map, url_map, title_order)
    """
    ozet_path = ozet_dir / f"{source}.json"
    icerik_path = ICERIKLER_DIR / f"{source}.json"

    ozet_data = load_json_file(ozet_path)
    # İçerik dosyasını sıralamayı koruyarak yükle
    icerik_data = load_json_file(icerik_path, preserve_order=True)
    
    # İçerik dosyasındaki başlıkların sırasını al
    title_order = get_content_order(icerik_data)

    summary_map: Dict[str, str] = {}
    content_map: Dict[str, List[Dict[str, str]]] = {}
    url_map: Dict[str, str] = {}

    # Özet dosyasını işle
    if isinstance(ozet_data, dict):
        for title, payload in ozet_data.items():
            summary = _extract_summary(payload)
            url = _extract_url(payload)
            if summary:
                summary_map[str(title)] = summary
            if url:
                url_map[str(title)] = url

    # İçerik dosyasını işle
    if isinstance(icerik_data, (dict, OrderedDict)):
        for title, payload in icerik_data.items():
            content = _extract_content(payload)
            url = _extract_url(payload)
            if content:
                content_map[str(title)] = content
            if url and str(title) not in url_map:
                url_map[str(title)] = url

    return summary_map, content_map, url_map, title_order


def normalize_entries(
    summary_map: Dict[str, str],
    content_map: Dict[str, List[Dict[str, str]]],
    url_map: Dict[str, str],
    title_order: List[str],
) -> List[Dict[str, Any]]:
    """Tüm başlıkları birleştirip normalize et. Sıralama içerik dosyasındaki sıraya göre yapılır."""
    # Tüm mevcut başlıkları topla
    all_titles = set(content_map.keys()) | set(summary_map.keys())
    
    # Sıralama: Önce içerik dosyasındaki sıraya göre (title_order), sonra diğerleri alfabetik
    ordered_titles = []
    seen_titles = set()
    
    # İçerik dosyasındaki sıraya göre ekle
    for title in title_order:
        if title in all_titles:
            ordered_titles.append(title)
            seen_titles.add(title)
    
    # Kalan başlıkları alfabetik olarak ekle (içerik dosyasında olmayan ama özet dosyasında olanlar)
    remaining_titles = sorted(all_titles - seen_titles)
    ordered_titles.extend(remaining_titles)

    entries: List[Dict[str, Any]] = []
    for title in ordered_titles:
        summary = summary_map.get(title)
        content = content_map.get(title)
        url = url_map.get(title)

        entry = {
            "title": title,
            "url": url,
            "summary": summary,
            "content_blocks": content,
            "raw_json": json.dumps(
                {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "content": content,
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
        entries.append(entry)

    # Sadece ilk 20 haberi göster
    return entries[:20]


def create_app() -> "Flask":
    if Flask is None:
        raise RuntimeError(
            "Flask bulunamadı. Lütfen `pip install Flask` komutuyla kurup tekrar deneyin."
        )

    # Template klasörünü mutlak yol olarak belirt
    template_path = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_path))

    @app.after_request
    def add_cors_headers(response):  # type: ignore[override]
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        return response

    @app.route("/", methods=["GET"])
    def index():
        sources = discover_news_sources(OZETLER_DIR)
        selected_source = request.args.get("source") or (sources[0] if sources else None)

        entries: List[Dict[str, Any]] = []
        error = None

        if selected_source:
            try:
                summary_map, content_map, url_map, title_order = load_news_data(selected_source, OZETLER_DIR)
                entries = normalize_entries(summary_map, content_map, url_map, title_order)
            except FileNotFoundError as exc:
                abort(404, description=str(exc))
            except Exception as exc:
                error = str(exc)
                entries = []

        return render_template(
            "json_viewer.html",
            sources=sources,
            selected_source=selected_source,
            entries=entries,
            error=error,
            page_type="llama",
        )

    @app.route("/mistral", methods=["GET"])
    def mistral():
        sources = discover_news_sources(OZETLER_MISTRAL_DIR)
        selected_source = request.args.get("source") or (sources[0] if sources else None)

        entries: List[Dict[str, Any]] = []
        error = None

        if selected_source:
            try:
                summary_map, content_map, url_map, title_order = load_news_data(selected_source, OZETLER_MISTRAL_DIR)
                entries = normalize_entries(summary_map, content_map, url_map, title_order)
            except FileNotFoundError as exc:
                abort(404, description=str(exc))
            except Exception as exc:
                error = str(exc)
                entries = []

        return render_template(
            "json_viewer.html",
            sources=sources,
            selected_source=selected_source,
            entries=entries,
            error=error,
            page_type="mistral",
        )

    @app.route("/api/sources", methods=["GET"])
    def api_sources():
        try:
            model_key, directory = resolve_model_directory(request.args.get("model"))
        except ValueError as exc:  # Geçersiz model parametresi
            return jsonify({"error": str(exc)}), 400

        sources = discover_news_sources(directory)
        return jsonify({"model": model_key, "sources": sources})

    @app.route("/api/entries", methods=["GET"])
    def api_entries():
        source = request.args.get("source")
        if not source:
            return jsonify({"error": "source parametresi zorunlu."}), 400

        try:
            model_key, directory = resolve_model_directory(request.args.get("model"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        limit_param = request.args.get("limit")
        limit = None
        if limit_param:
            try:
                limit = max(1, min(int(limit_param), 50))
            except ValueError:
                return jsonify({"error": "limit sayısal olmalıdır."}), 400

        try:
            summary_map, content_map, url_map, title_order = load_news_data(
                source, directory
            )
            entries = normalize_entries(
                summary_map, content_map, url_map, title_order
            )
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:  # pragma: no cover - beklenmeyen hatalar
            return jsonify({"error": str(exc)}), 500

        if limit is not None:
            entries = entries[:limit]

        payload = [
            {
                "id": f"{model_key}:{source}:{entry['title']}",
                "title": entry["title"],
                "summary": entry.get("summary"),
                "url": entry.get("url"),
                "source": source,
                "model": model_key,
            }
            for entry in entries
        ]
        return jsonify({"model": model_key, "source": source, "entries": payload})

    return app


app = create_app() if Flask is not None else None


def _preview_entries(source: str, limit: int, ozet_dir: Path = OZETLER_DIR) -> Tuple[str, List[Dict[str, Any]]]:
    """CLI için ön izleme."""
    summary_map, content_map, url_map, title_order = load_news_data(source, ozet_dir)
    entries = normalize_entries(summary_map, content_map, url_map, title_order)[:limit]
    return source, entries


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Haber özetleri ve içeriklerini web arayüzüyle görüntüle."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Mevcut haber kaynaklarını listele ve çık.",
    )
    parser.add_argument(
        "--preview",
        metavar="KAYNAK",
        help="Belirtilen kaynağın ilk kayıtlarını terminalde göster.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Ön izleme sırasında gösterilecek kayıt sayısı.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Yerleşik Flask sunucusunu (debug kapalı) başlat.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="--serve ile kullanılacak host (varsayılan 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="--serve ile kullanılacak port (varsayılan 5000).",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list:
        sources = discover_news_sources()
        if not sources:
            print("Hiç haber kaynağı bulunamadı.")
            return 0
        print("Mevcut haber kaynakları:")
        for name in sources:
            print(f"- {name}")
        return 0

    if args.preview:
        try:
            source, entries = _preview_entries(args.preview, args.limit)
            print(f"{source} kaynağından ilk {len(entries)} kayıt:\n")
            for entry in entries:
                print(f"# {entry['title']}")
                if entry.get("url"):
                    print(f"URL: {entry['url']}")
                if entry.get("summary"):
                    summary_preview = entry["summary"][:200]
                    print(f"Özet: {summary_preview}{'…' if len(entry['summary']) > 200 else ''}")
                if entry.get("content_blocks"):
                    print(f"İçerik: {len(entry['content_blocks'])} blok")
                print()
        except Exception as exc:
            print(f"Hata: {exc}", file=__import__("sys").stderr)
            return 1
        return 0

    if args.serve:
        if app is None:
            parser.error(
                "Yerleşik sunucuyu çalıştırmak için önce Flask kurmalısınız (pip install Flask)."
            )
        app.run(host=args.host, port=args.port, debug=False)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

