from pathlib import Path
from aspose_html_normalizer import normalize_aspose_html

ROOT = Path(__file__).parent.parent

_DEFAULT_INPUT_DIR = ROOT / "input"
_DEFAULT_IMAGE_MAP = ROOT / "image_map.json"
_DEFAULT_OUTPUT_HTML = ROOT / "temp" / "preprocessed.html"


def reconstruct_html(
    input_html: Path = None,
    image_map_path: Path = None,
    output_html: Path = None,
):
    """
    Normalizes Aspose HTML by delegating to aspose_html_normalizer.
    Maintains backwards compatibility for function signature.
    """
    if input_html is None:
        html_files = list(_DEFAULT_INPUT_DIR.glob("*.html"))
        if len(html_files) != 1:
            raise RuntimeError(
                f"Expected exactly one HTML file in {_DEFAULT_INPUT_DIR}, "
                f"found {len(html_files)}."
            )
        input_html = html_files[0]

    if image_map_path is None:
        image_map_path = _DEFAULT_IMAGE_MAP

    if output_html is None:
        output_html = _DEFAULT_OUTPUT_HTML

    metrics = normalize_aspose_html(
        input_html_path=Path(input_html),
        output_html_path=Path(output_html),
        image_map_path=Path(image_map_path),
    )
    return metrics


if __name__ == "__main__":
    reconstruct_html()