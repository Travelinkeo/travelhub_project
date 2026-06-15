import importlib.util
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Ensure project root is in PYTHONPATH
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
logger.debug(f"sys.path set to: {sys.path}")

# Import the registry to register parsers if they self‑register elsewhere
try:
    from apps.automation.parsers.registry import registry
except Exception as e:
    logger.warning(f"Unable to import registry: {e}. We'll load parsers manually.")
    registry = None


def load_legacy_parsers() -> list:
    """Dynamically import all legacy parser modules and return instantiated objects.
    The legacy parsers live in `apps/automation/parsers/legacy` and each defines a
    class inheriting from `BaseTicketParser` (named *Parser*)."""
    parsers_dir = Path(__file__).resolve().parents[2] / "apps" / "automation" / "parsers" / "legacy"
    parser_instances = []
    for file in parsers_dir.glob("*_parser.py"):
        module_name = file.stem
        spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to import {file.name}: {e}")
            continue
        # Find the parser class (subclass of BaseTicketParser)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            try:
                from apps.automation.parsers.base_parser import BaseTicketParser

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseTicketParser)
                    and attr is not BaseTicketParser
                ):
                    parser_instances.append(attr())
                    logger.info(f"Loaded parser {attr.__name__} from {file.name}")
            except Exception:
                continue
    return parser_instances


def get_sample_files(base_dir: Path):
    """Yield all files (recursively) under the given base directory."""
    for root, _, files in os.walk(base_dir):
        for f in files:
            yield Path(root) / f


def run_parser(parser, file_path: Path):
    try:
        # Determine file type
        if file_path.suffix.lower() == ".pdf":
            # Extract text from PDF using pdfminer
            from pdfminer.high_level import extract_text as pdf_extract_text

            text = pdf_extract_text(str(file_path))
        else:
            with open(file_path, "rb") as fp:
                raw = fp.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
        result = parser.parse(text, "")
        logger.info(f"✅ {file_path.name}: parsed with {parser.__class__.__name__}")
        return True
    except Exception as e:
        logger.error(f"❌ {file_path.name}: {parser.__class__.__name__} error: {e}")
        return False


def main():
    samples_root = Path(r"C:/Users/ARMANDO/Downloads/Boletos Pruebas")
    parsers = []
    if registry:
        # If parsers were registered elsewhere, use them
        parsers = registry.get_all_parsers()
    if not parsers:
        parsers = load_legacy_parsers()
    logger.info(f"Total parsers loaded: {len(parsers)}")
    summary = {}
    for file_path in get_sample_files(samples_root):
        # Determine file type and extract text
        if file_path.suffix.lower() == ".pdf":
            from pdfminer.high_level import extract_text as pdf_extract_text

            text = pdf_extract_text(str(file_path))
        else:
            with open(file_path, "rb") as fp:
                raw = fp.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")

        matched = False
        for parser in parsers:
            try:
                # Some parsers may implement a quick can_parse on raw text
                # Ensure we pass the extracted text (already obtained earlier as `text`)
                if parser.can_parse(text):
                    success = run_parser(parser, file_path)
                    summary.setdefault(parser.__class__.__name__, {"ok": 0, "fail": 0})
                    if success:
                        summary[parser.__class__.__name__]["ok"] += 1
                    else:
                        summary[parser.__class__.__name__]["fail"] += 1
                    matched = True
                    break
            except Exception as e:
                logger.error(f"Error during can_parse for {parser.__class__.__name__}: {e}")
        if not matched:
            logger.warning(f"⚠️ No parser matched for {file_path.name}")
    logger.info("--- Parsing Summary ---")
    for name, stats in summary.items():
        logger.info(f"{name}: {stats['ok']} success, {stats['fail']} failure")


if __name__ == "__main__":
    main()
