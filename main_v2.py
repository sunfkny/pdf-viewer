import itertools
import json
import pathlib
import re
import shutil
import subprocess

PDFJS_VERSION = "2.5.207"
PDFJS_DIR = pathlib.Path("./pdf.js")
SPARSE_DIRS = ["web", "l10n", "external"]

subprocess.run(["pnpm", "install", f"pdfjs-dist@{PDFJS_VERSION}"], shell=True)

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
        '<script src="viewer.js" type="module-shim"></script>',
        '<script src="./src/viewer.js" type="module"></script>',
    )
    .replace(
        '<link rel="resource" type="application/l10n" href="locale/locale.json">',
        '<link rel="resource" type="application/l10n" href="/locale/locale.json">',
    )
    .replace(
        '<script defer src="../node_modules/es-module-shims/dist/es-module-shims.js"></script>',
        "",
    )
)
index_html = re.sub(
    r'(<script type="importmap">[^<]+<\/script>)',
    "",
    index_html,
)
pathlib.Path("./index.html").write_text(index_html)

IMPORT_MAP = {
    "pdfjs-web": "pdfjs-web/build/pdf.min.js",
    "pdfjs-lib": "pdfjs-dist/build/pdf.mjs",
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
            'await import("./pdf.worker.js")',
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
            '"./pdf.worker.js"',
        )
        .replace(
            'import("pdfjs-web/',
            'import("./',
        )
        .replace(
            'import "../external/webL10n/l10n.js"',
            'import "./external/webL10n/l10n.js"',
        )
        .replace(
            'from "pdfjs-dist/build/pdf.mjs"',
            'from "pdfjs-dist/build/pdf.js"',
        )
        .replace(
            'if (origin !== viewerOrigin && protocol !== "blob:") {',
            "if (false) {",
        )
        .replace(
            '"../src/worker_loader.js"',
            '"./pdf.worker.js"',
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
shutil.rmtree("./public/locale")
shutil.copytree("./pdf.js/l10n", "./public/locale", dirs_exist_ok=True)
locale_data = []
for f in pathlib.Path("./pdf.js/l10n").glob("*/viewer.properties"):
    locale = f.parent.name
    locale_data.append(
        f"""
[{locale}]
@import url({locale}/viewer.properties)
"""
    )
pathlib.Path("./public/locale/locale.properties").write_text("\n".join(locale_data))


wasm_dir = pathlib.Path("public/wasm")
wasm_dir.mkdir(parents=True, exist_ok=True)
for f in itertools.chain(
    PDFJS_DIR.joinpath("external/openjpeg").glob("*.wasm"),
    [PDFJS_DIR.joinpath("external/openjpeg/openjpeg_nowasm_fallback.js")],
    PDFJS_DIR.joinpath("external/openjpeg").glob("LICENSE_*"),
    PDFJS_DIR.joinpath("external/qcms").glob("*.wasm"),
    PDFJS_DIR.joinpath("external/qcms").glob("LICENSE_*"),
):
    if not f.exists():
        continue
    shutil.copy(f, wasm_dir.joinpath(f.name))

webL10n = PDFJS_DIR.joinpath("external/webL10n")
if webL10n.exists():
    shutil.copytree(
        webL10n,
        "./src/external/webL10n",
        dirs_exist_ok=True,
    )
shutil.copy("./node_modules/pdfjs-dist/build/pdf.worker.js", "./public/pdf.worker.js")

subprocess.run(["pnpx", "prettier", "./index.html", "-w"], shell=True)
