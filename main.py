import itertools
import json
import pathlib
import re
import shutil
import subprocess

PDFJS_DIR = pathlib.Path("./pdf.js")
package_json = json.loads(pathlib.Path("package.json").read_text())
PDFJS_VERSION = package_json["dependencies"]["pdfjs-dist"]
assert re.match(r"^\d+\.\d+\.\d+$", PDFJS_VERSION), (
    "pdfjs-dist version is not exactly specified in package.json"
)

SPARSE_DIRS = ["web", "l10n", "external"]

if not PDFJS_DIR.exists():
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            "https://github.com/mozilla/pdf.js.git",
            str(PDFJS_DIR),
        ],
        check=True,
    )

subprocess.run(["git", "sparse-checkout", "init", "--cone"], cwd=PDFJS_DIR, check=True)
subprocess.run(
    ["git", "sparse-checkout", "set", *SPARSE_DIRS], cwd=PDFJS_DIR, check=True
)
subprocess.run(["git", "fetch", "--tags"], cwd=PDFJS_DIR, check=True)
subprocess.run(["git", "checkout", f"v{PDFJS_VERSION}"], cwd=PDFJS_DIR, check=True)

index_html = (
    pathlib.Path("./pdf.js/web/viewer.html")
    .read_text()
    .replace(
        '<link rel="stylesheet" href="viewer.css">',
        '<link rel="stylesheet" href="./src/viewer.css">',
    )
    .replace(
        '<script src="viewer.js" type="module"></script>',
        '<script src="./src/viewer.js" type="module"></script>',
    )
    .replace(
        '<link rel="resource" type="application/l10n" href="locale/locale.json">',
        '<link rel="resource" type="application/l10n" href="/locale/locale.json">',
    )
)
index_html = re.sub(
    r'(<script type="importmap">[^<]+<\/script>)',
    "",
    index_html,
)
pathlib.Path("./index.html").write_text(index_html)

IMPORT_MAP = {
    "pdfjs-lib": "pdfjs-dist/build/pdf.mjs",
    "fluent-bundle": "@fluent/bundle/esm/index.js",
    "fluent-dom": "@fluent/dom/esm/index.js",
    "cached-iterable": "cached-iterable/src/index.mjs",
    "web-alt_text_manager": "./alt_text_manager.js",
    "web-annotation_editor_params": "./annotation_editor_params.js",
    "web-download_manager": "./download_manager.js",
    "web-external_services": "./genericcom.js",
    "web-new_alt_text_manager": "./new_alt_text_manager.js",
    "web-null_l10n": "./genericl10n.js",
    "web-pdf_attachment_viewer": "./pdf_attachment_viewer.js",
    "web-pdf_cursor_tools": "./pdf_cursor_tools.js",
    "web-pdf_document_properties": "./pdf_document_properties.js",
    "web-pdf_find_bar": "./pdf_find_bar.js",
    "web-pdf_layer_viewer": "./pdf_layer_viewer.js",
    "web-pdf_outline_viewer": "./pdf_outline_viewer.js",
    "web-pdf_presentation_mode": "./pdf_presentation_mode.js",
    "web-pdf_sidebar": "./pdf_sidebar.js",
    "web-pdf_thumbnail_viewer": "./pdf_thumbnail_viewer.js",
    "web-preferences": "./genericcom.js",
    "web-print_service": "./pdf_print_service.js",
    "web-secondary_toolbar": "./secondary_toolbar.js",
    "web-signature_manager": "./signature_manager.js",
    "web-toolbar": "./toolbar.js",
}


def replace_imports(text: str):
    for k, v in IMPORT_MAP.items():
        text = text.replace(f'from "{k}";', f'from "{v}";')
    return text


def replace_text(text: str):
    return (
        text.replace(
            "../web/",
            "/",
        )
        .replace(
            'await import("pdfjs/pdf.worker.js")',
            f'await import("https://registry.npmmirror.com/pdfjs-dist/{PDFJS_VERSION}/files/build/pdf.worker.mjs")',
        )
        .replace(
            "if (version !== viewerVersion) {",
            "if (false) {",
        )
        .replace(
            '"compressed.tracemonkey-pldi-09.pdf"',
            '"https://mozilla.github.io/pdf.js/web/compressed.tracemonkey-pldi-09.pdf"',
        )
        .replace(
            "var validateFileURL = function (file) {",
            "var validateFileURL = function (file) {\nreturn;\n",
        )
        .replace(
            "import(sandboxBundleSrc)",
            "import(/* @vite-ignore */ sandboxBundleSrc)",
        )
        .replace(
            'await import(AppOptions.get("debuggerSrc"))',
            'await import(/* @vite-ignore */ AppOptions.get("debuggerSrc"))',
        )
        .replace(
            '"../src/pdf.worker.js"',
            '"https://registry.npmmirror.com/pdfjs-dist/5.3.93/files/build/pdf.worker.mjs"',
        )
    )


for f in pathlib.Path("./pdf.js/web").glob("*.js"):
    pathlib.Path("./src").joinpath(f.name).write_text(
        replace_text(replace_imports(f.read_text()))
    )

for f in pathlib.Path("./pdf.js/web").glob("*.css"):
    pathlib.Path("./src").joinpath(f.name).write_text(
        f.read_text()
        .replace("url(images/", "url(/images/")
        .replace('url("images/', 'url("/images/')
    )

shutil.copytree("./pdf.js/web/images", "./public/images", dirs_exist_ok=True)
shutil.copytree("./pdf.js/l10n", "./public/locale", dirs_exist_ok=True)
locale_data = {}
for f in pathlib.Path("./pdf.js/l10n").glob("*/viewer.ftl"):
    locale = f.parent.name
    locale_data[locale.lower()] = f"{locale}/viewer.ftl"
pathlib.Path("./public/locale/locale.json").write_text(
    json.dumps(locale_data, separators=(",", ":"))
)

wasm_dir = pathlib.Path("public/wasm")
wasm_dir.mkdir(parents=True, exist_ok=True)
for f in itertools.chain(
    PDFJS_DIR.joinpath("external/openjpeg").glob("*.wasm"),
    [PDFJS_DIR.joinpath("external/openjpeg/openjpeg_nowasm_fallback.js")],
    PDFJS_DIR.joinpath("external/openjpeg").glob("LICENSE_*"),
    PDFJS_DIR.joinpath("external/qcms").glob("*.wasm"),
    PDFJS_DIR.joinpath("external/qcms").glob("LICENSE_*"),
):
    shutil.copy(f, wasm_dir.joinpath(f.name))

subprocess.run(["pnpx", "prettier", "./index.html", "-w"], shell=True)
