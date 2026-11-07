"""Contrato SNS exercitado com SDK simulado; não consulta credenciais nem rede."""

import builtins
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from publicar_sns import publicar


ARN = "arn:aws:sns:sa-east-1:000000000000:teste-local"


class BotoCoreErrorSimulado(Exception):
    pass


class ClientErrorSimulado(Exception):
    pass


class PublicacaoSNS(unittest.TestCase):
    def setUp(self):
        self.cliente = Mock()
        self.cliente.publish.return_value = {"MessageId": "id-simulado"}
        self.sdk = types.ModuleType("boto3")
        self.sdk.client = Mock(return_value=self.cliente)
        botocore = types.ModuleType("botocore")
        excecoes = types.ModuleType("botocore.exceptions")
        excecoes.BotoCoreError = BotoCoreErrorSimulado
        excecoes.ClientError = ClientErrorSimulado
        botocore.exceptions = excecoes
        modulos = patch.dict(sys.modules, {
            "boto3": self.sdk,
            "botocore": botocore,
            "botocore.exceptions": excecoes,
        })
        modulos.start()
        self.addCleanup(modulos.stop)
        ambiente = patch.dict(os.environ, {
            "AWS_SNS_TOPIC_ARN": ARN,
            "AWS_DEFAULT_REGION": "sa-east-1",
        }, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)

    def publicar(self):
        return publicar({}, {}, assunto="FarmTech: teste", corpo="Mensagem simulada")

    def test_publicacao_confirma_message_id_e_preserva_conteudo(self):
        self.assertEqual(self.publicar(), "id-simulado")
        self.sdk.client.assert_called_once_with("sns", region_name="sa-east-1")
        self.cliente.publish.assert_called_once_with(
            TopicArn=ARN, Subject="FarmTech: teste", Message="Mensagem simulada",
        )

    def test_arn_ausente_recusa_antes_de_criar_cliente(self):
        os.environ.pop("AWS_SNS_TOPIC_ARN")
        with self.assertRaisesRegex(RuntimeError, "Defina AWS_SNS_TOPIC_ARN"):
            self.publicar()
        self.sdk.client.assert_not_called()

    def test_arn_invalido_ou_nao_standard_recusa_antes_do_cliente(self):
        invalidos = [
            "nao-e-arn:sa-east-1:topico",
            "arn:aws:sqs:sa-east-1:000000000000:topico",
            "arn:aws:sns:sa-east-1:conta:topico",
            "arn:aws:sns:sa-east-1:000000000000:",
            "arn:aws:sns:sa-east-1:000000000000:topico.fifo",
            ARN + ":assinatura",
        ]
        for arn in invalidos:
            with self.subTest(arn=arn):
                os.environ["AWS_SNS_TOPIC_ARN"] = arn
                with self.assertRaisesRegex(RuntimeError, "ARN válido"):
                    self.publicar()
                self.sdk.client.assert_not_called()

    def test_arn_de_outra_regiao_recusa_antes_do_cliente(self):
        os.environ["AWS_SNS_TOPIC_ARN"] = ARN.replace("sa-east-1", "us-east-1")
        with self.assertRaisesRegex(RuntimeError, "região sa-east-1"):
            self.publicar()
        self.sdk.client.assert_not_called()

    def test_regiao_do_cliente_divergente_recusa_antes_do_cliente(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        with self.assertRaisesRegex(RuntimeError, "AWS_DEFAULT_REGION"):
            self.publicar()
        self.sdk.client.assert_not_called()

    def test_regiao_ausente_ou_vazia_usa_padrao(self):
        for valor in (None, "", "   "):
            with self.subTest(regiao=valor):
                if valor is None:
                    os.environ.pop("AWS_DEFAULT_REGION", None)
                else:
                    os.environ["AWS_DEFAULT_REGION"] = valor
                self.sdk.client.reset_mock()
                self.assertEqual(self.publicar(), "id-simulado")
                self.sdk.client.assert_called_once_with("sns", region_name="sa-east-1")

    def test_dependencia_ausente_tem_erro_explicativo(self):
        importar = builtins.__import__

        def sem_boto3(nome, *args, **kwargs):
            if nome == "boto3":
                raise ImportError("ausência simulada")
            return importar(nome, *args, **kwargs)

        with patch("builtins.__import__", side_effect=sem_boto3):
            with self.assertRaisesRegex(RuntimeError, "Instale boto3"):
                self.publicar()
        self.sdk.client.assert_not_called()

    def test_falha_na_criacao_do_cliente_e_tratada(self):
        erro = BotoCoreErrorSimulado("falha simulada")
        self.sdk.client.side_effect = erro
        with self.assertRaisesRegex(RuntimeError, "Não foi possível publicar") as contexto:
            self.publicar()
        self.assertIs(contexto.exception.__cause__, erro)
        self.cliente.publish.assert_not_called()

    def test_falhas_de_publicacao_sao_tratadas(self):
        for classe in (BotoCoreErrorSimulado, ClientErrorSimulado):
            with self.subTest(erro=classe.__name__):
                erro = classe("falha simulada")
                self.cliente.publish.side_effect = erro
                with self.assertRaisesRegex(RuntimeError, "Não foi possível publicar") as contexto:
                    self.publicar()
                self.assertIs(contexto.exception.__cause__, erro)

    def test_sem_message_id_valido_nao_confirma_publicacao(self):
        for resposta in ({}, {"MessageId": None}, {"MessageId": ""}, {"MessageId": 123}):
            with self.subTest(resposta=resposta):
                self.cliente.publish.return_value = resposta
                with self.assertRaisesRegex(RuntimeError, "não confirmou"):
                    self.publicar()


if __name__ == "__main__":
    unittest.main()
