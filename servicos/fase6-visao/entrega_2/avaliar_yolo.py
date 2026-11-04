"""Avaliação futura, em processo novo, de pesos YOLOv5 locais e confiáveis.

Não obtém código/pesos nem instala dependências. O checkout Git local deve
estar íntegro e na revisão indicada. O carregador legado pode desserializar
objetos Python: forneça apenas os artefatos cuja procedência foi conferida.
Os resultados impressos constituem uma nova execução, sem substituir as
evidências históricas. A compatibilidade funcional deste fluxo está pendente.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


RAIZ = Path(__file__).resolve().parents[1]
REVISAO_CUSTOMIZADA = "4add2aff"
SHA256_CUSTOMIZADA = "93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61"
CLASSES = {0: "banana", 1: "milho"}


def argumentos(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abordagem", choices=("customizada", "padrao"), required=True)
    parser.add_argument("--yolo-repo", type=Path, required=True,
                        help="Checkout Git local existente, contendo hubconf.py; não será alterado.")
    parser.add_argument("--revisao",
                        help="SHA completo de 40 dígitos, obrigatório para padrão. Para customizada, "
                             "a omissão exige HEAD com o prefixo histórico 4add2aff.")
    parser.add_argument("--pesos", type=Path,
                        help="Checkpoint .pt local e confiável; padrão: artefato da abordagem em entrega_2/.")
    parser.add_argument("--dataset", type=Path, default=RAIZ / "dataset" / "test",
                        help="Raiz do conjunto de teste, com images/ e labels/ (padrão: dataset/test).")
    parser.add_argument("--json", action="store_true",
                        help="Emite um único relatório JSON; suprime logs das bibliotecas.")
    args = parser.parse_args(argv)
    if args.revisao is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", args.revisao):
        parser.error("--revisao exige SHA completo; branches, tags e abreviações não são aceitas.")
    if args.abordagem == "padrao" and args.revisao is None:
        parser.error("YOLO padrão exige --revisao explícita; sua revisão histórica não foi fixada.")
    args.pesos = (args.pesos or (
        RAIZ / "entrega_2" / "modelos" / "yolov5s_custom_exp60_best.pt"
        if args.abordagem == "customizada" else RAIZ / "entrega_2" / "yolov5s.pt"
    )).resolve()
    args.dataset = args.dataset.resolve()
    args.yolo_repo = args.yolo_repo.resolve()
    return args


def git_local(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, encoding="utf-8", env=env,
    )
    return result.stdout.strip()


def verificar_fonte(args):
    repo = args.yolo_repo
    if not (repo / "hubconf.py").is_file():
        raise ValueError("--yolo-repo precisa conter hubconf.py local; nenhum download será realizado.")
    if Path(git_local(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("--yolo-repo deve apontar para a raiz do checkout Git da YOLOv5.")
    head = git_local(repo, "rev-parse", "--verify", "HEAD^{commit}").lower()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("HEAD não corresponde a um commit SHA-1 completo verificável.")
    if args.revisao and head != args.revisao.lower():
        raise ValueError(f"HEAD {head} difere de --revisao {args.revisao}.")
    if args.abordagem == "customizada":
        # A resolução falha para prefixos ausentes ou ambíguos no checkout local.
        revisao_historica = git_local(
            repo, "rev-parse", "--verify", f"{REVISAO_CUSTOMIZADA}^{{commit}}",
        ).lower()
        if head != revisao_historica or not head.startswith(REVISAO_CUSTOMIZADA):
            raise ValueError("A avaliação customizada exige o commit único de carregamento histórico 4add2aff.")
    # Inclui fontes ignoradas/não rastreadas que poderiam sobrepor imports.
    # Pesos locais e __pycache__ não fazem parte desta seleção de código.
    alteracoes = git_local(
        repo, "status", "--porcelain", "--untracked-files=all", "--ignored=matching", "--",
        "*.py", "*.yaml", "*.yml", "*.txt", "*.toml", "*.cfg", "*.ini", "*.json", "*.pyd", "*.so", "*.pth",
    )
    if alteracoes:
        raise ValueError("Checkout contém código/configuração alterado, não rastreado ou ignorado. "
                         "A fonte deve ser verificável antes da avaliação:\n" + alteracoes)
    return head


def sha256(arquivo):
    digest = hashlib.sha256()
    with arquivo.open("rb") as stream:
        for parte in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(parte)
    return digest.hexdigest()


def verificar_entradas(args):
    if not args.pesos.is_file() or args.pesos.suffix.lower() != ".pt":
        raise ValueError(f"Checkpoint .pt local ausente: {args.pesos}")
    digest = sha256(args.pesos)
    if args.abordagem == "customizada" and digest != SHA256_CUSTOMIZADA:
        raise ValueError("SHA-256 não corresponde ao checkpoint customizado preservado de 60 épocas.")
    fotos = []
    anotacoes = {}
    for cultura in CLASSES.values():
        arquivos = sorted((args.dataset / "images" / cultura).glob("*.jpg"))
        if len(arquivos) != 4:
            raise ValueError(f"Esperadas quatro imagens de teste JPG por classe: {cultura}.")
        for foto in arquivos:
            arquivo = args.dataset / "labels" / cultura / f"{foto.stem}.txt"
            caixas = {0: [], 1: []}
            for linha in arquivo.read_text(encoding="utf-8").splitlines():
                valores = list(map(float, linha.split()))
                if len(valores) != 5 or not all(map(math.isfinite, valores)):
                    raise ValueError(f"Rótulo YOLO inválido: {arquivo}")
                classe, cx, cy, largura, altura = valores
                if classe not in CLASSES or not (0 <= cx <= 1 and 0 <= cy <= 1
                                                and 0 < largura <= 1 and 0 < altura <= 1):
                    raise ValueError(f"Classe/coordenadas inválidas: {arquivo}")
                caixas[int(classe)].append((cx, cy, largura, altura))
            fotos.append(foto)
            anotacoes[foto] = caixas
    return fotos, anotacoes, digest


def impedir_mistura_modulos():
    conflitantes = [nome for nome in sys.modules
                    if nome in ("models", "utils") or nome.startswith(("models.", "utils."))]
    if conflitantes:
        raise RuntimeError("Módulos YOLO já importados; execute este script em um novo processo Python.")


def bloquear_rede_e_processos(evento, dados, repo):
    """Permite apenas consultas locais exatas; bloqueia rede, shells e instaladores."""
    if evento in ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname"):
        raise OSError("Avaliação offline: acesso à rede bloqueado.")
    if evento == "subprocess.Popen":
        executavel, argv, _cwd, _env = dados
        # Strings de comando/shells não entram na lista de consultas permitidas.
        if isinstance(argv, (list, tuple)) and argv:
            nome = Path(os.fsdecode(executavel)).name.lower()
            argumentos = tuple(os.fsdecode(valor) for valor in argv[1:])
            if nome == "fc-list" and argumentos in (("--help",), ("--format=%{file}\\n",)):
                return  # Consultas utilizadas pelo font_manager do Matplotlib.
            if nome == "system_profiler" and argumentos == ("-xml", "SPFontsDataType"):
                return
            if nome in ("git", "git.exe"):
                if len(argumentos) >= 2 and argumentos[0] == "-C":
                    if Path(argumentos[1]).resolve() != repo:
                        raise PermissionError("Consulta Git fora da fonte YOLO verificada.")
                    argumentos = argumentos[2:]
                consultas_git = {
                    ("describe", "--tags", "--long", "--always"),
                    ("describe", "--long", "--always"),
                    ("rev-parse", "HEAD"), ("rev-parse", "--short", "HEAD"),
                    ("rev-parse", "--show-toplevel"), ("rev-parse", "--is-inside-work-tree"),
                }
                if argumentos in consultas_git:
                    return
    if evento in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn"):
        # OSError permite os fallbacks de probes opcionais das bibliotecas.
        raise PermissionError("Avaliação isolada: comando externo não permitido; instalações bloqueadas.")


@contextmanager
def compatibilidade_posix_windows():
    """Ajuste temporário apenas no Windows; restaura referências públicas/privadas."""
    if os.name != "nt":
        yield
        return
    import pathlib

    alvos = [pathlib]
    try:
        interno = importlib.import_module("pathlib._local")
    except ModuleNotFoundError:
        interno = None
    if interno is not None and hasattr(interno, "PosixPath"):
        alvos.append(interno)
    originais = [(modulo, modulo.PosixPath) for modulo in alvos]
    try:
        for modulo, _original in originais:
            modulo.PosixPath = pathlib.WindowsPath
        yield
    finally:
        for modulo, original in originais:
            modulo.PosixPath = original


def avaliar(args, fotos, anotacoes):
    # Antes de qualquer import de framework ou código YOLO.
    os.environ["YOLO_AUTOINSTALL"] = "False"
    os.environ["YOLO_OFFLINE"] = "True"
    os.environ["WANDB_MODE"] = "disabled"
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    sys.dont_write_bytecode = True
    impedir_mistura_modulos()
    # O hook permanece até o encerramento deste processo independente.
    sys.addaudithook(lambda evento, dados: bloquear_rede_e_processos(evento, dados, args.yolo_repo))
    import torch
    from torchvision.ops import box_iou

    impedir_mistura_modulos()
    with compatibilidade_posix_windows():
        modelo = torch.hub.load(
            str(args.yolo_repo), "custom", path=str(args.pesos), source="local", device="cpu",
        )
    modelo.conf = 0.25
    modelo.eval()
    itens_nomes = enumerate(modelo.names) if isinstance(modelo.names, (list, tuple)) else modelo.names.items()
    nomes = {int(k): str(v).lower() for k, v in itens_nomes}
    if args.abordagem == "customizada":
        if nomes != CLASSES:
            raise ValueError(f"Classes customizadas inesperadas: {nomes}")
        mapeamento = {0: 0, 1: 1}
    else:
        bananas = [indice for indice, nome in nomes.items() if nome == "banana"]
        if len(nomes) != 80 or len(bananas) != 1:
            raise ValueError("Esperados pesos COCO de 80 classes, incluindo banana.")
        mapeamento = {0: bananas[0]}
    contagens = {classe: {"TP": 0, "FP": 0, "FN": 0} for classe in mapeamento}
    tempos = []
    por_imagem = []
    with torch.inference_mode():
        modelo(str(fotos[0]), size=640)  # Aquecimento excluído do tempo.
        for foto in fotos:
            inicio = time.perf_counter()
            resultado = modelo(str(foto), size=640)
            tempos.append((time.perf_counter() - inicio) * 1000)
            predicoes = resultado.xyxy[0].detach().cpu()
            altura, largura = resultado.ims[0].shape[:2]
            item = {"imagem": foto.name, "classes": {}}
            for classe, id_modelo in mapeamento.items():
                previstas = predicoes[predicoes[:, 5] == id_modelo]
                reais = [[(cx-w/2)*largura, (cy-h/2)*altura,
                          (cx+w/2)*largura, (cy+h/2)*altura]
                         for cx, cy, w, h in anotacoes[foto][classe]]
                usados = set()
                if len(previstas) and reais:
                    ious = box_iou(previstas[:, :4], torch.tensor(reais, dtype=torch.float32))
                    for i in torch.argsort(previstas[:, 4], descending=True).tolist():
                        for j in torch.argsort(ious[i], descending=True).tolist():
                            if float(ious[i, j]) >= 0.50 and j not in usados:
                                usados.add(j)
                                break
                tp = len(usados)
                fp, fn = len(previstas) - tp, len(reais) - tp
                for chave, valor in (("TP", tp), ("FP", fp), ("FN", fn)):
                    contagens[classe][chave] += valor
                item["classes"][CLASSES[classe]] = {"tp": tp, "fp": fp, "fn": fn}
                print(f"{foto.name} | {CLASSES[classe]}: TP={tp}, FP={fp}, FN={fn}")
            por_imagem.append(item)
    metricas = {}
    for classe, valores in contagens.items():
        tp, fp, fn = (valores[chave] for chave in ("TP", "FP", "FN"))
        precisao = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precisao * recall / (precisao + recall) if precisao + recall else 0
        metricas[CLASSES[classe]] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precisao, "recall": recall, "f1": f1,
        }
        print(f"{CLASSES[classe]}: Precision={precisao:.2%}; Recall={recall:.2%}; F1={f1:.2%}")
    print(f"Tempo médio (CPU, individual, após aquecimento): {sum(tempos)/len(tempos):.2f} ms/imagem")
    print("Limiar de confiança=0,25; IoU de associação=0,50; tamanho de inferência=640.")
    if args.abordagem == "padrao":
        print("Avaliação somente de banana; COCO não fornece classe específica de milho.")
    return {
        "experimento": "nova_avaliacao_independente_yolo",
        "abordagem": args.abordagem,
        "total_imagens": len(fotos),
        "metricas": metricas,
        "por_imagem": por_imagem,
        "tempo_medio_ms": sum(tempos) / len(tempos),
        "configuracao": {"confianca": 0.25, "iou_associacao": 0.50, "tamanho": 640},
        "ambiente": {"python": sys.version.split()[0], "torch": str(torch.__version__), "dispositivo": "CPU"},
    }


def _executar(args):
    head = verificar_fonte(args)
    fotos, anotacoes, digest = verificar_entradas(args)
    print("Nova avaliação; não substitui resultados históricos. Compatibilidade funcional a validar.")
    print(f"Fonte local: {args.yolo_repo}\nCommit: {head}\nPesos: {args.pesos}\nSHA-256: {digest}")
    relatorio = avaliar(args, fotos, anotacoes)
    relatorio.update({"revisao": head, "checkpoint_sha256": digest})
    return relatorio


def main(argv=None):
    args = argumentos(argv)
    if not args.json:
        return _executar(args)
    # Não persiste logs/artefatos. Mantém a saída JSON livre de mensagens do Hub.
    with open(os.devnull, "w", encoding="utf-8") as descarte:
        with redirect_stdout(descarte), redirect_stderr(descarte):
            relatorio = _executar(args)
    print(json.dumps(relatorio, ensure_ascii=False, allow_nan=False))
    return relatorio


if __name__ == "__main__":
    main()
