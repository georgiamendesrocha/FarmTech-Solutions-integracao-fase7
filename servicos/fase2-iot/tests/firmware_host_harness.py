"""Prepara testes host com trechos literais de src/prog1.ino, sem alterar o firmware.

O executavel testa apenas tres funcoes puras e suas constantes. Nao compila o
firmware ESP32 completo nem exercita GPIO, DHT22, Wokwi, serial ou hardware.
FARMTECH_CXX pode indicar o caminho de um compilador host ja instalado.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "src" / "prog1.ino"
CONSTANT_NAMES = (
    "PH_MIN_TOMATE", "PH_MAX_TOMATE", "UMIDADE_BAIXA_TOMATE",
    "UMIDADE_ALTA_TOMATE", "AJUSTE_FALTA_N", "AJUSTE_FALTA_P", "AJUSTE_FALTA_K",
)
FUNCTION_NAMES = ("calcularPhBase", "corrigirPhPorNutrientes", "decidirIrrigacaoTomate")


def mask_comments_and_literals(source):
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda match: re.sub(r"[^\n]", " ", match.group()), source)


def extract_constant(source, name):
    masked = mask_comments_and_literals(source)
    matches = list(re.finditer(r"(?m)^[ \t]*const\s+float\s+" + re.escape(name) + r"\s*=\s*[^;\n]+;", masked))
    if len(matches) != 1:
        raise ValueError(f"Esperada uma constante float {name}; encontradas {len(matches)}")
    return source[matches[0].start():matches[0].end()]


def extract_function(source, name):
    masked = mask_comments_and_literals(source)
    matches = list(re.finditer(r"(?m)^[ \t]*(?:float|bool)\s+" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{", masked))
    if len(matches) != 1:
        raise ValueError(f"Esperada uma definicao de {name}; encontradas {len(matches)}")
    match = matches[0]
    depth = 1
    for position in range(match.end(), len(masked)):
        depth += (masked[position] == "{") - (masked[position] == "}")
        if depth == 0:
            return source[match.start():position + 1]
    raise ValueError(f"Funcao {name} sem fechamento de chaves")


def literal_snippets(source):
    return [extract_constant(source, name) for name in CONSTANT_NAMES] + [
        extract_function(source, name) for name in FUNCTION_NAMES
    ]


def numeric_constants(source):
    """Valores literais para o modelo Python separado; nao executa C++."""
    constants = {}
    for name in CONSTANT_NAMES:
        expression = extract_constant(source, name).split("=", 1)[1].rstrip("; ")
        if not re.fullmatch(r"\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fF]?", expression):
            raise ValueError(f"Expressao nao literal em {name}; revisar o modelo Python")
        constants[name] = float(expression.strip().rstrip("fF"))
    return constants


def find_host_compiler():
    explicit = os.environ.get("FARMTECH_CXX")
    if explicit:
        candidate = shutil.which(explicit)
        if candidate is None:
            raise FileNotFoundError("FARMTECH_CXX nao aponta para compilador existente")
        return Path(candidate)
    for name in ("g++", "clang++", "c++", "cl", "clang-cl"):
        candidate = shutil.which(name)
        if candidate:
            return Path(candidate)
    if os.name != "nt":
        return None

    # Winget's portable toolchains may be installed before this shell reloads PATH.
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        candidates = sorted(packages.glob(
            "BrechtSanders.WinLibs.POSIX.UCRT_*/mingw64/bin/g++.exe"
        ), reverse=True)
        if candidates:
            return candidates[0]

    drive = Path(os.environ.get("SystemDrive", "C:") + "/")
    patterns = (
        "rtools*/**/bin/g++.exe", "msys64/*/bin/g++.exe", "MinGW/bin/g++.exe",
        "mingw64/bin/g++.exe", "tools/**/bin/g++.exe",
        "Program Files/LLVM/bin/clang++.exe", "Program Files/JetBrains/**/bin/g++.exe",
        "Program Files/Microsoft Visual Studio/*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe",
        "Program Files (x86)/Microsoft Visual Studio/*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe",
        "ProgramData/chocolatey/bin/g++.exe", "ProgramData/chocolatey/bin/clang++.exe",
        "ProgramData/chocolatey/lib/**/bin/g++.exe", "ProgramData/chocolatey/lib/**/bin/clang++.exe",
        "ProgramData/scoop/apps/**/bin/g++.exe", "ProgramData/scoop/apps/**/bin/clang++.exe",
    )
    for pattern in patterns:
        candidates = sorted(drive.glob(pattern), reverse=True)
        if candidates:
            return candidates[0]
    for pattern in ("scoop/apps/**/bin/g++.exe", "scoop/apps/**/bin/clang++.exe"):
        candidates = sorted(Path.home().glob(pattern), reverse=True)
        if candidates:
            return candidates[0]
    return None


CPP_CASES = r'''
static void check(bool condition, const char* label) {
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", label);
        std::exit(1);
    }
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const char* name = argv[1];
    if (std::strcmp(name, "isolated_n_missing") == 0) {
        check(decidirIrrigacaoTomate(70.0f, 6.3f, false, true, true), "N ausente, pH ideal: ON");
    } else if (std::strcmp(name, "same_values_n_present") == 0) {
        check(!decidirIrrigacaoTomate(70.0f, 6.3f, true, true, true), "Somente N presente: OFF");
    } else if (std::strcmp(name, "corrected_ph_stays_ideal") == 0) {
        const float corrected = corrigirPhPorNutrientes(6.6f, false, true, true);
        check(std::fabs(corrected - 6.3f) < 0.0001f, "pH base 6.6, sem N: pH corrigido 6.3");
        check(corrected >= PH_MIN_TOMATE && corrected <= PH_MAX_TOMATE, "pH corrigido permanece ideal");
        check(decidirIrrigacaoTomate(70.0f, corrected, false, true, true), "Ausencia de N liga com pH ideal");
    } else if (std::strcmp(name, "ph_outside_npk_full") == 0) {
        check(decidirIrrigacaoTomate(70.0f, 5.9f, true, true, true), "NPK completo, pH baixo: ON");
        check(decidirIrrigacaoTomate(70.0f, 6.9f, true, true, true), "NPK completo, pH alto: ON");
        check(!decidirIrrigacaoTomate(70.0f, PH_MIN_TOMATE, true, true, true), "pH minimo inclusivo: OFF");
        check(!decidirIrrigacaoTomate(70.0f, PH_MAX_TOMATE, true, true, true), "pH maximo inclusivo: OFF");
    } else if (std::strcmp(name, "moisture_boundaries") == 0) {
        check(decidirIrrigacaoTomate(44.99f, 6.3f, true, true, true), "Umidade baixa: ON");
        for (float humidity : {45.0f, 80.0f}) {
            check(!decidirIrrigacaoTomate(humidity, 6.3f, true, true, true), "Faixa intermediaria ideal: OFF");
            check(decidirIrrigacaoTomate(humidity, 6.3f, false, true, true), "Faixa intermediaria sem N: ON");
        }
        check(!decidirIrrigacaoTomate(80.01f, 5.0f, false, false, false), "Umidade alta tem prioridade: OFF");
    } else if (std::strcmp(name, "invalid_humidity") == 0) {
        for (float humidity : {-1.0f, 101.0f, NAN, INFINITY, -INFINITY})
            check(!decidirIrrigacaoTomate(humidity, 6.3f, false, true, true), "Umidade invalida: OFF");
    } else if (std::strcmp(name, "ph_mapping_and_adjustments") == 0) {
        check(calcularPhBase(0) == 14.0f, "ADC zero: pH14");
        check(calcularPhBase(4095) == 0.0f, "ADC maximo: pH0");
        check(std::fabs(calcularPhBase(2048) - 6.99829f) < 0.0001f, "ADC intermediario invertido");
        check(calcularPhBase(-1) == 14.0f && calcularPhBase(4096) == 0.0f, "pH base limitado");
        check(std::fabs(corrigirPhPorNutrientes(6.6f, false, false, false) - 5.9f) < 0.0001f, "Ajustes NPK acumulados");
        check(corrigirPhPorNutrientes(0.1f, false, false, false) == 0.0f, "pH corrigido limitado em zero");
        check(corrigirPhPorNutrientes(15.0f, true, true, true) == 14.0f, "pH corrigido limitado em14");
    } else if (std::strcmp(name, "invalid_ph") == 0) {
        check(decidirIrrigacaoTomate(70.0f, NAN, true, true, true), "pH NaN na faixa intermediaria: ON");
        check(decidirIrrigacaoTomate(70.0f, INFINITY, true, true, true), "pH infinito na faixa intermediaria: ON");
        check(!decidirIrrigacaoTomate(81.0f, NAN, true, true, true), "Umidade alta com pH invalido: OFF");
    } else if (std::strcmp(name, "other_nutrients_missing") == 0) {
        check(decidirIrrigacaoTomate(70.0f, 6.3f, true, false, true), "Somente P ausente: ON");
        check(decidirIrrigacaoTomate(70.0f, 6.3f, true, true, false), "Somente K ausente: ON");
    } else {
        return 2;
    }
    std::printf("PASS C++ host: %s\n", name);
    return 0;
}
'''


def build_source(source):
    prefix = (
        "// Trechos literais extraidos de src/prog1.ino; teste host parcial.\n"
        "#include <cmath>\n#include <cstdio>\n#include <cstdlib>\n"
        "#include <cstring>\n#include <initializer_list>\n"
        "using std::isnan;\nusing std::isinf;\n"
    )
    return prefix + "\n\n".join(literal_snippets(source)) + "\n" + CPP_CASES


def prepare_harness():
    source = FIRMWARE.read_text(encoding="utf-8-sig")
    prepared = build_source(source)
    directory = Path(tempfile.mkdtemp(prefix=".tmp_firmware_", dir=ROOT / "tests"))
    cpp_path = directory / "firmware_rules.cpp"
    cpp_path.write_text(prepared, encoding="utf-8")
    return directory, cpp_path


def compile_harness(compiler, directory, cpp_path):
    executable = directory / ("firmware_rules.exe" if os.name == "nt" else "firmware_rules")
    env = {**os.environ, "PATH": str(compiler.parent) + os.pathsep + os.environ.get("PATH", "")}
    if compiler.name.lower() in ("cl", "cl.exe", "clang-cl", "clang-cl.exe"):
        command = [str(compiler), "/nologo", "/EHsc", "/std:c++14", "/utf-8", str(cpp_path),
                   "/Fe" + str(executable), "/Fo" + str(directory / "firmware_rules.obj")]
    else:
        command = [str(compiler), "-std=c++11", "-O0", "-Wall", "-Wextra", str(cpp_path), "-o", str(executable)]
    result = subprocess.run(command, cwd=directory, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60)
    if result.returncode or not executable.is_file():
        raise AssertionError(f"Falha real ao compilar C++ host (nao e skip):\n{result.stdout}\n{result.stderr}")
    return executable, env
