"""Avalia a CNN preservada no teste, sem treinamento ou gravação de artefatos.

Os tempos impressos pertencem a esta nova execução e não substituem os resultados
históricos registrados no notebook comparacao_yolo_cnn_fase6.ipynb.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time


CLASSES = ("banana", "milho")
TAMANHO = 224
IMAGENS_POR_CLASSE = 4
RAIZ = Path(__file__).resolve().parent.parent


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Carrega a CNN .keras existente e avalia somente as oito imagens "
            "de teste em CPU. Não treina, instala, baixa ou salva arquivos. "
            "O relatório JSON é enviado à saída padrão."
        )
    )
    parser.add_argument(
        "--dataset", type=Path, default=RAIZ / "dataset",
        help="Raiz contendo test/images/{banana,milho} (padrão: dataset do projeto).",
    )
    parser.add_argument(
        "--modelo", type=Path,
        default=RAIZ / "entrega_2" / "modelos" / "cnn_do_zero_fase6.keras",
        help="Modelo .keras preservado (padrão: entrega_2/modelos/cnn_do_zero_fase6.keras).",
    )
    return parser.parse_args()


def caminhos_teste(dataset: Path) -> list[tuple[Path, int]]:
    """Verifica a divisão de teste antes de importar frameworks."""
    arquivos = []
    for indice, classe in enumerate(CLASSES):
        pasta = dataset / "test" / "images" / classe
        if not pasta.is_dir():
            raise ValueError(f"Diretório de teste ausente: {pasta}")
        fotos = sorted(pasta.glob("*.jpg"))
        if len(fotos) != IMAGENS_POR_CLASSE:
            raise ValueError(
                f"Esperadas {IMAGENS_POR_CLASSE} imagens .jpg de {classe}; "
                f"encontradas {len(fotos)} em {pasta}."
            )
        arquivos.extend((foto, indice) for foto in fotos)
    return arquivos


def carregar_imagens(arquivos, np, cv2):
    """Replica a célula 30: BGR→RGB, INTER_AREA, float32, escala 0–255."""
    imagens = []
    for foto, _ in arquivos:
        imagem = cv2.imread(str(foto))
        if imagem is None:
            raise ValueError(f"Falha ao ler a imagem de teste: {foto}")
        imagem = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
        imagem = cv2.resize(
            imagem, (TAMANHO, TAMANHO), interpolation=cv2.INTER_AREA
        )
        imagens.append(imagem)
    # O modelo contém Rescaling(1/255); não normalizar novamente aqui.
    return np.asarray(imagens, dtype=np.float32)


def metricas(reais, previstas) -> dict:
    """Matriz real×previsto e métricas one-vs-rest, sem scikit-learn."""
    matriz = [[0, 0], [0, 0]]
    for real, prevista in zip(reais, previstas):
        matriz[int(real)][int(prevista)] += 1

    por_classe = {}
    for indice, classe in enumerate(CLASSES):
        tp = matriz[indice][indice]
        fp = sum(linha[indice] for linha in matriz) - tp
        fn = sum(matriz[indice]) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        por_classe[classe] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
        }
    total = sum(sum(linha) for linha in matriz)
    acertos = sum(matriz[indice][indice] for indice in range(len(CLASSES)))
    return {
        "matriz_confusao_real_por_previsto": matriz,
        "por_classe": por_classe,
        "acertos": acertos,
        "total": total,
        "acuracia": acertos / total,
    }


def main() -> int:
    args = argumentos()
    try:
        modelo_path = args.modelo.resolve()
        dataset = args.dataset.resolve()
        if not modelo_path.is_file() or modelo_path.suffix.lower() != ".keras":
            raise ValueError(f"Modelo .keras existente não encontrado: {modelo_path}")
        arquivos = caminhos_teste(dataset)

        # Apenas o processo atual: CPU e ausência de caches Python gravados.
        # --help termina no argparse, antes destes imports e do carregamento.
        sys.dont_write_bytecode = True
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        import cv2
        import numpy as np
        import tensorflow as tf

        imagens = carregar_imagens(arquivos, np, cv2)
        modelo = tf.keras.models.load_model(
            modelo_path, compile=False, safe_mode=True
        )
        if tuple(modelo.input_shape) != (None, TAMANHO, TAMANHO, 3):
            raise ValueError(f"Entrada incompatível com RGB 224×224: {modelo.input_shape}")
        if tuple(modelo.output_shape) != (None, 1):
            raise ValueError(f"Saída incompatível com a classificação binária: {modelo.output_shape}")
        normalizacoes = [
            camada for camada in modelo.layers
            if isinstance(camada, tf.keras.layers.Rescaling)
        ]
        if len(normalizacoes) != 1 or not (
            np.isclose(normalizacoes[0].scale, 1 / 255)
            and np.isclose(normalizacoes[0].offset, 0)
        ):
            raise ValueError("O modelo deve conter uma camada Rescaling(1/255) sem offset.")

        # predict desativa aumento de dados e dropout usados no treinamento.
        modelo.predict(imagens[:1], verbose=0)
        inicio = time.perf_counter()
        probabilidades = np.asarray(
            modelo.predict(imagens, batch_size=len(imagens), verbose=0)
        ).ravel()
        tempo = time.perf_counter() - inicio
        if len(probabilidades) != len(arquivos) or not np.all(
            np.isfinite(probabilidades) & (probabilidades >= 0) & (probabilidades <= 1)
        ):
            raise ValueError("Predições inválidas: esperada uma probabilidade finita por imagem.")
        previstas = (probabilidades >= 0.5).astype(int)
        reais = [indice for _, indice in arquivos]

        relatorio = {
            "experimento": "nova_avaliacao_independente_cnn",
            "observacao": "Estes tempos não substituem os resultados históricos do notebook.",
            "modelo": str(modelo_path),
            "dataset": str(dataset),
            "ambiente": {
                "python": sys.version.split()[0], "tensorflow": tf.__version__,
                "dispositivo": "CPU",
            },
            "classes": {str(indice): classe for indice, classe in enumerate(CLASSES)},
            "pre_processamento": "RGB 224x224, INTER_AREA, float32 [0,255]; Rescaling interno",
            "limiar_milho": 0.5,
            "metricas": metricas(reais, previstas),
            "tempos_nova_execucao": {
                "protocolo": (
                    "Uma predição de aquecimento com uma imagem, excluída da medição; "
                    "predict em um lote de oito imagens. Exclui leitura, pré-processamento "
                    "e carregamento do modelo."
                ),
                "inferencia_total_s": tempo,
                "media_ms_por_imagem": tempo * 1000 / len(arquivos),
            },
            "predicoes": [
                {
                    "imagem": str(foto.relative_to(dataset)),
                    "real": CLASSES[real], "prevista": CLASSES[int(prevista)],
                    "probabilidade_milho": float(probabilidade),
                }
                for (foto, real), prevista, probabilidade
                in zip(arquivos, previstas, probabilidades)
            ],
        }
        print(json.dumps(relatorio, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except ImportError as erro:
        print(f"Erro: dependência indisponível ou incompatível: {erro}", file=sys.stderr)
    except Exception as erro:
        print(f"Erro na avaliação da CNN: {erro}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
